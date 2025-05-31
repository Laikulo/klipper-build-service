function start_kconfig(form) {
    const kconfig_tar_path = "kconfig_bundles/" + document.getElementById("kconfig_bundle").value + '.tar'
    const starting_conf = document.getElementById('starting_config')
    if (starting_conf.value) {
        let conf_reader = new FileReader()
        conf_reader.onload = (_) => {
            send_file_to_vm('klipper.config', conf_reader.result)
        }
        conf_reader.readAsArrayBuffer(starting_conf.files[0])
    }
    fetch(kconfig_tar_path).then( (response) => {
        if (response.ok) {
            response.arrayBuffer().then((buf) => {
                send_file_to_vm('kconfig.tar', buf)
                send_chars_to_vm('\x07')
                window.vm_terminal.focus()
            })
        } else {
            console.log("Failed to retrieve bundle")
        }
    }).catch((reason) => console.log(reason))
    return false
}

function send_file_to_vm(path, data_in) {
    let buf = new Uint8Array(data_in)
    let buf_len = buf.length
    let buf_addr = _malloc(buf_len)
    console.log("Importing " + buf_len + "b into " + path + "...")
    HEAPU8.set(buf, buf_addr)
    fs_import_file(path, buf_addr, buf_len)
    console.log('Import of ' + path + " complete")
}

function send_chars_to_vm(chars) {
    window.term_handler(chars)
}

let setupTerm = (cols, rows, handler) => {
    let web_terminal = new window.Terminal({
        cols: cols,
        rows: rows,
        cursorBlink: true
    })
    web_terminal.onData(handler)
    web_terminal.open(document.getElementById('terminal'))
    window.vm_terminal = web_terminal
    window.vm_input = handler
    return {
        write: (x) => {web_terminal.write(x)},
        writeln: (x) => {web_terminal.writeln(x)},
        getSize: () => { return [cols, rows] }
    }
}

window.kbs_init = function () {
    let kbs_menuconfig_form = document.getElementById('kconfig_form')
    kbs_menuconfig_form.onsubmit = (ev) => {
        ev.preventDefault()
        start_kconfig(kbs_menuconfig_form)
    }

    start_vm(null, null, setupTerm, {
        url: "menuconfig-riscv64.cfg",
        scriptBase: 'jslinux/'
    })
}