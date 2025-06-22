#!/usr/bin/env python3
import abc
import dataclasses
from dataclasses import field, dataclass
import os
import shutil
from abc import abstractmethod
from dataclasses import dataclass
from enum import IntEnum
from os import stat_result
from pathlib import Path
from tarfile import TarFile, TarInfo
from typing import Optional, List, final, Union, Callable

MODE_SHIFT = 3 * 4


class VirtualFsDataType(IntEnum):
    UNKN = 0o00
    FIFO = 0o01
    CHAR = 0o02
    DIR = 0o04
    BLK = 0o06
    FILE = 0o10
    LINK = 0o12
    SOCK = 0o14

    @classmethod
    def from_mode(cls, in_value: int):
        # four octal digits, three bits per
        return cls(in_value >> MODE_SHIFT)

    def to_mode(self, in_mode: int):
        return (self.value << MODE_SHIFT) | in_mode


def tar_basename(in_name):
    tok = in_name.rsplit("/",1)
    if len(tok) > 1:
        return tok[1]
    else:
        return tok[0]


@dataclass
class VirtualFS(object):
    version: int = 1
    revision: int = 1
    root_file_id: Optional[int] = None
    root_directory: Optional['VirtualFSDirectory'] = None
    fs_dir: Optional[Path] = None
    next_file_id: int = 1
    max_size: int = 2 ** 30
    file_size_blocks: int = 0
    block_size: int = 4096

    def to_dict(self):
        return {
            'Version': self.version,
            'Revision': self.revision,
            'NextFileID': "%x" % self.next_file_id,
            'FSFileCount': "%x" % (self.next_file_id - 1),
            'FSSize': self.file_size_blocks * self.block_size,
            'FSMaxSize': int(self.max_size),
            'Key': "",  # TODO: Figure out what this is for
            'RootID': self.root_file_id
        }

    def assign_file_id(self):
        file_id = self.next_file_id
        self.next_file_id += 1
        return file_id

    def bytes_to_blocks(self, bytes_count):
        return (
                (bytes_count // self.block_size) +
                (1 if bytes_count % self.block_size else 0)
        )

    def count_file_size(self, byte_count: int):
        self.file_size_blocks += self.bytes_to_blocks(byte_count)

    def path_for_file(self, file_id: int) -> Path:
        assert self.fs_dir is not None
        return self.fs_dir / 'files' / ('%016x' % file_id)

    def _head_text(self):
        return "\n".join(
            [f"{k}: {v}" for k, v in self.to_dict().items()] + [""]
        )

    def from_path(self, path: Path):
        self.root_file_id = self.assign_file_id()
        self.root_directory = VirtualFSDirectory.entity_from_path(self, path, True)

    def from_tar(self, tarfile: TarFile):
        self.root_file_id = self.assign_file_id()
        self.root_directory = VirtualFSDirectory.entity_from_path(self, tarfile, True)

    def render_to_dir(self, target_dir):
        if target_dir:
            self.fs_dir = target_dir
        assert self.fs_dir is not None
        self.fs_dir.mkdir(exist_ok=True)
        if not self.root_file_id:
            self.root_file_id = self.assign_file_id()
        lock_file = self.fs_dir / 'lock'
        lock_file.touch(exist_ok=True)
        files_path = self.fs_dir / 'files'
        files_path.mkdir(exist_ok=True)
        self.root_directory.render_to_dir(files_path)
        head_file = self.fs_dir / 'head'
        head_file.write_text(self._head_text())


@dataclass
class VirtualFSObject(abc.ABC):
    _fs: VirtualFS
    _node_type = VirtualFsDataType.UNKN
    node_mode: int = 0o640
    node_uid: int = 0
    node_gid: int = 0
    node_mtime: int = 0
    node_mtime_nanos: int = 0
    node_filename: str = ""

    def get_size(self):
        return 0

    def get_mode(self):
        return self._node_type.to_mode(self.node_mode)

    def dir_entry(self):
        return "%06o %d %d %d.%d %s" % (
            self.get_mode(), self.node_uid, self.node_gid, self.node_mtime, self.node_mtime_nanos, self.node_filename)

    def _dir_entry_with_size(self):
        return "%06o %d %d %d %d.%d %s" % (
            self.get_mode(), self.node_uid, self.node_gid, self.get_size(), self.node_mtime, self.node_mtime_nanos,
            self.node_filename)

    def render_to_dir(self, files_dir: Path) -> None:
        pass

    def _load_from_stat(self, stat_obj: stat_result):
        self.node_mode = stat_obj.st_mode
        self.node_uid = stat_obj.st_uid
        self.node_gid = stat_obj.st_gid
        self.node_mtime = stat_obj.st_mtime_ns // 1_000_000_000
        self.node_mtime_nanos = stat_obj.st_mtime_ns % 1_000_000_000

    def _load_from_tarinfo(self, tarinfo: TarInfo):
        self.node_mode = tarinfo.mode
        self.node_uid = tarinfo.uid
        self.node_gid = tarinfo.gid
        self.node_mtime = tarinfo.mtime
        self.node_mtime_nanos = 0  # tars don't keep mtimes more than 1ms

    @staticmethod
    @final
    def from_path(fs: VirtualFS, path: Path, recursive=False) -> 'VirtualFSObject':
        if path.is_symlink():
            return VirtualFSSymlink.entity_from_path(fs, path, recursive)
        elif path.is_file():
            return VirtualFSFile.entity_from_path(fs, path, recursive)
        elif path.is_dir():
            return VirtualFSDirectory.entity_from_path(fs, path, recursive)
        elif path.is_char_device():
            return VirtualFSCharDev.entity_from_path(fs, path, recursive)
        elif path.is_block_device():
            return VirtualFSBlockDevice.entity_from_path(fs, path, recursive)
        elif path.is_socket():
            return VirtualFSSocket.entity_from_path(fs, path, recursive)
        elif path.is_fifo():
            return VirtualFSFifo.entity_from_path(fs, path, recursive)
        else:
            raise ValueError(f"Unexpected filetype found: {path}")

    @staticmethod
    def get_cls_for(source: Union[Path,TarFile,TarInfo]):
        if isinstance(source, Path):
            if source.is_symlink():
                return VirtualFSSymlink
            elif source.is_file():
                return VirtualFSFile
            elif source.is_dir():
                return VirtualFSDirectory
            elif source.is_char_device():
                return VirtualFSCharDev
            elif source.is_block_device():
                return VirtualFSBlockDevice
            elif source.is_socket():
                return VirtualFSSocket
            elif source.is_fifo():
                return VirtualFSFifo
        elif isinstance(source, TarInfo):
            if source.issym():
                return VirtualFSSymlink
            elif source.isreg():
                return VirtualFSFile
            elif source.isdir():
                return VirtualFSDirectory
            elif source.ischr():
                return VirtualFSCharDev
            elif source.isblk():
                return VirtualFSBlockDevice
            # Sockets may not be supported in tars?
            # There's probably some extension I'll need to parse
            # does make sense though
            elif source.isfifo():
                return VirtualFSFifo
            else:
                raise ValueError(f"Unable to determine virtFS type for tarinfo {source}",)
        else:
            raise ValueError(f"Unexpected type {type(source)} for virtfs entity ")

    @classmethod
    def entity_from(cls, fs, source: Union[Path,TarFile,TarInfo], recursive=False):
        if isinstance(source, TarFile):
            return VirtualFSDirectory.entity_from_path(fs, source, recursive)
        cls_tgt = cls.get_cls_for(source)
        if isinstance(source, Path):
            return cls_tgt.entity_from_path(fs, source, recursive)
        elif isinstance(source, TarInfo):
            return cls_tgt.entity_from_tarinfo(fs, source, recursive)
        else:
            raise ValueError("Bad type in entity_from")

    @classmethod
    @abstractmethod
    def entity_from_path(cls, fs, path: Path, recursive=False) -> 'VirtualFSObject':
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def entity_from_tarinfo(cls, fs, tarinfo: TarInfo, recursive=False):
        raise NotImplementedError


@dataclass
class VirtualFSFifo(VirtualFSObject):
    _node_type = VirtualFsDataType.FIFO

    @classmethod
    def entity_from_path(cls, fs, path: Path, recursive=False) -> 'VirtualFSObject':
        obj = cls(fs)
        obj._load_from_stat(path.stat())
        obj.node_filename = path.name
        return obj

    @classmethod
    def entity_from_tarinfo(cls, fs, tarinfo: TarInfo, recursive=False):
        obj = cls(fs)
        obj._load_from_tarinfo(tarinfo)
        obj.node_filename = tar_basename(tarinfo.name)
        return obj


@dataclass
class VirtualFSCharDev(VirtualFSObject):
    _node_type = VirtualFsDataType.CHAR
    node_dev_major: int = 0
    node_dev_minor: int = 0

    def dir_entry(self):
        return "%06o %d %d %d %d %d.%d %s" % (self.get_mode(),
                                              self.node_uid, self.node_gid,
                                              self.node_dev_major, self.node_dev_minor,
                                              self.node_mtime, self.node_mtime_nanos,
                                              self.node_filename)

    def _load_from_stat(self, stat_obj: stat_result):
        super()._load_from_stat(stat_obj)
        self.node_dev_major = os.major(stat_obj.st_rdev)
        self.node_dev_minor = os.minor(stat_obj.st_rdev)

    def _load_from_tarinfo(self, tarinfo: TarInfo):
        super()._load_from_tarinfo(tarinfo)
        self.node_dev_major = tarinfo.devmajor
        self.node_dev_minor = tarinfo.devminor

    @classmethod
    def entity_from_path(cls, fs, path: Path, recursive=False) -> 'VirtualFSObject':
        obj = cls(fs)
        path_stat = path.stat()
        obj._load_from_stat(path_stat)
        obj.node_filename = path.name
        return obj

    @classmethod
    def entity_from_tarinfo(cls, fs, tarinfo: TarInfo, recursive=False):
        obj = cls(fs)
        obj._load_from_tarinfo(tarinfo)
        obj.node_filename = tar_basename(tarinfo.name)
        return obj



@dataclass
class VirtualFSDirectory(VirtualFSObject):
    _node_type = VirtualFsDataType.DIR
    __tar_tree = None
    __tar_base = None
    __tar_file: Optional[TarFile] = None
    children: List[VirtualFSObject] = field(default_factory=list)

    def get_size(self):
        return len(self.children)

    def _self_dir_entry(self) -> str:
        return super().dir_entry()

    def dir_entry(self) -> str:
        ret = []
        if not self.is_root_dir:
            ret.append(self._self_dir_entry())
        ret += [e.dir_entry() for e in self.children]
        ret.append(".")
        return "\n".join(ret)

    @property
    def is_root_dir(self):
        return self._fs.root_directory == self

    def _header_text(self):
        return \
            f"Version: {self._fs.version}\n" \
            f"Revision: {self._fs.revision}\n" \
            "\n"

    def render_to_dir(self, files_dir: Path) -> None:
        # If we are the root FS, we need to render the file tree
        if self._fs.root_directory == self:
            file_id = self._fs.root_file_id
            listing_path = self._fs.path_for_file(file_id)
            with listing_path.open("w+") as listing:
                listing.write(self._header_text())
                listing.write(self.dir_entry())
                listing.write("\n")
                self._fs.count_file_size(listing.tell())
        # Render the children to disk (files only)
        for child in self.children:
            child.render_to_dir(files_dir)

    @classmethod
    def entity_from_path(cls, fs, path: Union[Path,TarFile], recursive=False) -> 'VirtualFSDirectory':
        obj = cls(fs)
        if isinstance(path, Path):
            obj._load_from_stat(path.stat())
            obj.node_filename = path.name
            if recursive:
                obj.children = [VirtualFSObject.from_path(fs, f, recursive) for f in path.iterdir()]
        elif isinstance(path, TarFile):
            obj.__tar_file = path
            root_member = path.getmember('.')
            obj._load_from_tarinfo(root_member)
            # A tarfile's filename is always the root, which has no true name.
            obj.node_filename = "."
            obj.__tar_base = "."  # Root of archive
            obj.__build_tar_tree(path)
            if recursive:
                obj.__handle_tar_children()
        else:
            raise NotImplementedError
        return obj

    def __build_tar_tree(self, tar_file: TarFile):
        self.__tar_tree = {}
        for member in tar_file.getmembers():
            member: TarInfo
            tokens = member.path.rsplit("/",1)
            if len(tokens) > 1:
                member_path = tokens[0]
                member_name = tokens[1]
            else:
                member_path = ""
                member_name = tokens[0]
                if member_name == ".":
                    # Skip the root node
                    continue
            if member_path not in self.__tar_tree:
                self.__tar_tree[member_path] = []
            self.__tar_tree[member_path].append(member_name)
        pass

    def __tar_children(self):
        if self.__tar_base in self.__tar_tree:
            return [ self.__tar_file.getmember(self.__tar_base + "/" + f) for f in  self.__tar_tree[self.__tar_base] ]
        else:
            # Empty Directory
            return []

    def __handle_tar_children(self):
        for child in self.__tar_children():
            child: TarInfo
            if child.isdir():
                child_dir = VirtualFSDirectory.entity_from_tarinfo(self._fs, child, False)
                child_dir.__tar_file = self.__tar_file
                child_dir.__tar_tree = self.__tar_tree
                child_dir.__tar_base = child.path
                child_dir.__handle_tar_children()
                self.children.append(child_dir)
            else:
                self.children.append(VirtualFSObject.entity_from(self._fs, child, True))
            print(child)
        pass

    def tar_extract(self, member: TarInfo):
        if not self.is_root_dir:
            raise ValueError("Tried to extract tar data from non root")
        return self.__tar_file.extractfile(member)

    @classmethod
    def entity_from_tarinfo(cls, fs, tarinfo: TarInfo, recursive=False):
        obj = cls(fs)
        obj._load_from_tarinfo(tarinfo)
        obj.node_filename = tar_basename(tarinfo.name)
        if recursive:
            obj.__handle_tar_children()
        return obj


@dataclass
class VirtualFSBlockDevice(VirtualFSCharDev):
    _node_type = VirtualFsDataType.BLK


@dataclass
class VirtualFSFile(VirtualFSObject):
    _node_type = VirtualFsDataType.FILE
    _node_file_id: Optional[int] = None
    _node_size: int = 0
    __source_file: Optional[Path] = None
    __tar_info: Optional[TarInfo] = None

    def get_size(self):
        return self._node_size

    def dir_entry(self):
        if self._node_size:
            if self._node_file_id is None:
                self._node_file_id = self._fs.assign_file_id()
            return self._dir_entry_with_size() + (" %x" % self._node_file_id)
        else:
            # Zero-length files are not assigned an ID, so one is not in the listing
            return self._dir_entry_with_size()

    def render_to_dir(self, files_dir: Path) -> None:
        if self.get_size() > 0:
            if self.__tar_info:
                self._fs.path_for_file(self._node_file_id).write_bytes(self._fs.root_directory.tar_extract(self.__tar_info).read())
            elif self.__source_file:
                shutil.copy(self.__source_file, self._fs.path_for_file(self._node_file_id))
            else:
                raise ValueError(f"Could not get content for file {self.node_filename}")
            self._fs.count_file_size(self.get_size())

    def _load_from_stat(self, stat_obj: stat_result):
        super()._load_from_stat(stat_obj)
        self._node_size = stat_obj.st_size

    def _load_from_tarinfo(self, tarinfo: TarInfo):
        super()._load_from_tarinfo(tarinfo)
        self._node_size = tarinfo.size

    @classmethod
    def entity_from_path(cls, fs: VirtualFS, path: Path, recursive=False) -> 'VirtualFSObject':
        obj = cls(fs)
        obj.__source_file = path
        path_stat = path.stat()
        obj._load_from_stat(path_stat)
        if obj._node_size:
            obj._node_file_id = fs.assign_file_id()
        obj.node_filename = path.name
        return obj

    @classmethod
    def entity_from_tarinfo(cls, fs, tarinfo: TarInfo, recursive=False):
        obj = cls(fs)
        obj._load_from_tarinfo(tarinfo)
        obj._node_size = tarinfo.size
        obj.node_filename = tar_basename(tarinfo.name)
        if obj._node_size:
            obj._node_file_id = fs.assign_file_id()
            obj.__tar_info = tarinfo
        return obj


@dataclass
class VirtualFSSymlink(VirtualFSObject):
    _node_type = VirtualFsDataType.LINK
    target: str = ""

    def dir_entry(self):
        return super().dir_entry() + (" %s" % self.target)

    @classmethod
    def entity_from_path(cls, fs, path: Path, recursive=False) -> 'VirtualFSObject':
        obj = cls(fs)
        obj._load_from_stat(path.lstat())
        obj.node_filename = path.name
        obj.target = path.readlink()
        return obj

    @classmethod
    def entity_from_tarinfo(cls, fs, tarinfo: TarInfo, recursive=False):
        obj = cls(fs)
        obj._load_from_tarinfo(tarinfo)
        obj.node_filename = tar_basename(tarinfo.name)
        obj.target = tarinfo.linkname
        return obj


@dataclass
class VirtualFSSocket(VirtualFSObject):
    _node_type = VirtualFsDataType.SOCK

    @classmethod
    def entity_from_path(cls, fs, path: Path, recursive=False) -> 'VirtualFSObject':
        obj = cls(fs)
        obj._load_from_stat(path.stat())
        obj.node_filename = path.name
        return obj

    @classmethod
    def entity_from_tarinfo(cls, fs, tarinfo: TarInfo, recursive=False):
        obj = cls(fs)
        obj._load_from_tarinfo(tarinfo)
        obj.node_filename = tar_basename(tarinfo.name)
        return obj
