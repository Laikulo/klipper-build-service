VM_STATES = ["OFF", "BOOTING", "READY", "RUNNING", "RESETTING"]
window.vm_state = 0 // Default to OFF

// Called by the WASM side
function on_file_export(filename, data) {
    if (filename === 'klipper.config') {
        on_config_generated(data)
    } else {
        alert(filename + " unexpectedly exported ignoring it")
        console.log(data)
    }
}

function on_config_generated(config_data) {
    window.current_config = config_data
    modal('config_done')
}

function discard_config() {
    window.current_config = null
    modal(null)
}

function download_config(filename) {
    let config_url = URL.createObjectURL(window.current_config)
    let config_dl = document.createElement('a');
    config_dl.setAttribute("download", filename)
    config_dl.setAttribute('style', "display:none;")
    config_dl.innerHTML = filename
    config_dl.href = config_url
    document.body.appendChild(config_dl)
    config_dl.click()
    document.body.removeChild(config_dl)
}

function modal(name) {
    if (window.active_modal === name) {
        return // nothing to do
    }
    if (window.active_modal) {
        document.getElementById("modal_" + window.active_modal).classList.remove('modal_active')
    }
    if (name) {
        window.active_modal = name
        document.getElementById("modal_" + name).classList.add('modal_active')
        document.getElementById('terminal').classList.add('blurred')
    } else {
        window.active_modal = null
        document.getElementById('terminal').classList.remove('blurred')
    }
}

function vm_state_change(new_state) {
    window.vm_state = new_state
    document.getElementById('vm_state_text').textContent = VM_STATES[new_state]
    set_led('on', (new_state > 0))
    set_led('working', (new_state !== 0 && new_state !== 2))
}

function run_menuconfig_v3(ev) {
    ev.preventDefault()
    let file_list = null
    if (document.getElementById('form_v3_config_file').checked) {
        let file_chooser = document.getElementById('form_v3_config_file_chooser')
        if (!file_chooser.value) {
            alert("File mode selected, but no file uploaded. Please check input and try again!")
            return false
        }
        file_list = file_chooser
    }
    let kconfig_bundle_url = window.kconfig_project.revisions[document.getElementById('form_v3_version').selectedOptions[0].value].getKConfigBundleUrl()
    launch_kconfig(kconfig_bundle_url, file_list)
    return false
}

function launch_kconfig(kconfig_bundle_url, conf_file) {
    if (conf_file && conf_file.value) {
        let conf_reader = new FileReader()
        conf_reader.onload = (_) => {
            send_file_to_vm('klipper.config', conf_reader.result)
        }
        conf_reader.readAsArrayBuffer(conf_file.files[0])
    }
    fetch(kconfig_bundle_url).then((response) => {
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
        cols: cols, rows: rows, cursorBlink: true
    })
    web_terminal.onData(handler)
    web_terminal.open(document.getElementById('terminal'))
    window.vm_terminal = web_terminal
    window.vm_input = handler
    return {
        write: (x) => {
            web_terminal.write(proc_vm_input(x))
        }, writeln: (x) => {
            web_terminal.writeln(x)
        }, getSize: () => {
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

async function populate_versions(project, target_selector) {
    window.kconfig_project = window.kconfig_repo.getProject(project)
    let loading_opt = document.createElement("option")
    loading_opt.innerText = 'Loading...'
    loading_opt.disabled = true
    target_selector.replaceChildren(loading_opt)
    target_selector.selectedIndex = 0
    let new_opts = (await window.kconfig_project.getRevisions()).entries().map(e => {
        let opt = document.createElement("option")
        opt.value = e[0]
        opt.innerText = e[1].human_version
        return opt
    })
    target_selector.replaceChildren(...new_opts)
    target_selector.disabled = false
}

window.kbs_init = function () {
    window.kconfig_repo = new KBSRevisionRepo("./revisions")
    window.kconfig_project = undefined
    let populate_promise = populate_versions('klipper', document.getElementById('form_v3_version'))
    document.getElementById('form_v3_upstream').onchange = event => {
        let submit_button = document.getElementById('form_v3_submit')
        submit_button.disabled = true
        populate_versions(event.target.value, document.getElementById('form_v3_version')).then(_ => {
            submit_button.disabled = false
        })
    }

    window.active_modal = null
    if (window.location.hash.includes("novm")) {
        return
    }
    document.getElementById('kconfig_form_v3').onsubmit = run_menuconfig_v3
    start_vm(null, null, setupTerm, {
        url: "menuconfig-riscv64.cfg", scriptBase: 'jslinux/'
    })
    vm_state_change(1)
}