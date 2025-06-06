class KBSRevisionRepo {
    constructor(base_url) {
        this.base_url = base_url
        this._projects = {}
    }

    getProject(project_name) {
        if (this._projects.hasOwnProperty(project_name)) {
            return this._projects[project_name]
        } else {
            let obj = new KBSRevisionProject(this, project_name)
            this._projects[project_name] = obj
            return obj
        }
    }
}

class KBSRevisionProject {
    constructor(repo, project_name) {
        this.repo = repo
        this.project_name = project_name
        this.csv_data = null
        this.revisions = null
    }

    async getCSV() {
        let csv_url = new URL(this.repo.base_url + "/" + this.project_name + ".csv", window.location)
        let csv_resp =  await fetch(csv_url)
        if(csv_resp.ok) {
            return csv_resp.text()
        } else {
            throw "Could not get CSV!"
        }
    }

    async getRevisions() {
        if (!this.revisions) {
            this.csv_data = (await this.getCSV()).split('\n')
            this.revisions = this.csv_data.filter(x => x !== "").map( x => {
                return new KBSRevision(this).loadFromCSV(x)
            })
        }
        return this.revisions
    }

    async getRevisionBySha(git_sha) {
        for(let rev of (await this.getRevisions())) {
            if(rev.git_sha === git_sha) {
                return rev
            }
        }
        return null
    }

    async getRevisionByVer(query) {
        for(let rev of (await this.getRevisions())) {
            if(rev.human_version === query) {
                return rev
            }
        }
        return null
    }

}

class KBSRevision {
    constructor(project) {
        this.project = project
        this.git_sha = undefined
        this.human_version = undefined
        this.kconfig_hash = undefined
    }

    loadFromCSV(csv_line) {
        let csv_fields = csv_line.split(",")
        this.git_sha = csv_fields[0]
        this.human_version = csv_fields[1]
        this.kconfig_hash = csv_fields[2]
        return this
    }

    getKConfigBundleUrl() {
        return new URL(this.project.repo.base_url + "/kconfig-bundles/" + this.project.project_name + "/kconfig-" + this.kconfig_hash + ".tar", window.location)
    }
}
