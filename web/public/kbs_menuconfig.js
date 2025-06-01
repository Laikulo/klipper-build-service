VM_STATES = [
    "OFF",
    "BOOTING",
    "READY",
    "RUNNING",
    "RESETTING"
]
window.vm_state = 0 // Default to OFF

function on_file_export(filename, blob) {
    alert(filename + "exported")
    console.log(blob)
}

function on_config_generated(config_data) {
}

function update_modal_form(ev) {
    let conf_file = document.getElementById('config_file')
    if (ev.target.id === "config_mode_upload") {
        conf_file.disabled = false
        if (!conf_file.value) {
            conf_file.click()
        }
    } else if (ev.target.id === "config_mode_scratch") {
        conf_file.disabled = true
    }
}

function vm_state_change(new_state) {
    window.vm_state = new_state
    document.getElementById('vm_state_text').textContent = VM_STATES[new_state]
    set_led('on', (new_state > 0))
}

function run_menuconfig_v3(ev) {
    ev.preventDefault()
    let file_list = null
    if (document.getElementById('form_v3_config_file').checked) {
        file_chooser = document.getElementById('form_v3_config_file_chooser')
        if (!file_chooser.files) {
            alert("File mode selected, but no file uploaded. Please check input and try again!")
            return false
        }
        file_list = file_chooser
    }
    launch_kconfig('take1', file_list)
    return false
}

function launch_kconfig(kconfig_bundle_name, conf_file) {
    const kconfig_tar_path = "kconfig_bundles/" + kconfig_bundle_name + '.tar'
    if (conf_file && conf_file.value) {
        let conf_reader = new FileReader()
        conf_reader.onload = (_) => {
            send_file_to_vm('klipper.config', conf_reader.result)
        }
        conf_reader.readAsArrayBuffer(conf_file.files[0])
    }
    fetch(kconfig_tar_path).then((response) => {
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

/* Special returns:
 * ASCII SOT 0x02 - Ready
 * ASCII ACK 0x06 - Ack start comand
 * ASCII EOT 0x03 - Done
 */
function proc_vm_input(str) {
    for (let c of str) {
        if (c === '\x02') {
            vm_state_change(2)
        } else if (c === '\x03') {
            vm_state_change(4)
        } else if (c === '\x06') {
            if (window.vm_state === 2) {
                vm_state_change(3)
            }
        }
    }
    return str
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
        write: (x) => {
            web_terminal.write(proc_vm_input(x))
        },
        writeln: (x) => {
            web_terminal.writeln(x)
        },
        getSize: () => {
            return [cols, rows]
        }
    }
}

function set_led(name, state) {
    let led = document.getElementById('led_' + name)
    if (state) {
        led.classList.add('led_on')
    } else {
        led.classList.remove('led_on')
    }
}

function on_disk_act(is_active) {
    set_led('access', is_active)
}

window.kbs_init = function () {
    document.getElementById('kconfig_form_v3').onsubmit = run_menuconfig_v3
    start_vm(null, null, setupTerm, {
        url: "menuconfig-riscv64.cfg",
        scriptBase: 'jslinux/'
    })
    vm_state_change(1)
}