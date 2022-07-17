# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

import contextlib
from git import *
from git.exc import *
from .file_helpers import run_in_exc


class Updater:
    def __init__(self, repo, branch="main", app_url=None) -> None:
        self.branch = branch
        self.repo = repo
        self.app_url = app_url

    @run_in_exc
    def gen_changelog(self, repo_, msg, url):
        branch_name = repo_.active_branch.name
        remote_name = "upstream"
        dm = f"HEAD..{remote_name}/{branch_name}"
        d_form = "⏰ %D/%M/%Y :: %H:%M:%S"
        return "".join(
            f"[#{repo_change.count}]({url}commit/{repo_change}) [{repo_change.committed_datetime.strftime(d_form)}]: {repo_change.summary} 👨‍💻 {repo_change.author}\n"
            for repo_change in repo_.iter_commits(dm)
        )

    @run_in_exc
    def init_repo(self):
        try:
            repo = Repo()
        except GitCommandError as e:
            e._msg = "Looks like there is some issues while initiating the repo."
            raise GitCommandError from e
        except InvalidGitRepositoryError:
            repo = Repo.init()
            if "upstream" in repo.remotes:
                origin = repo.remote("upstream")
            else:
                origin = repo.create_remote("upstream", self.repo)
            origin.fetch()
            repo.create_head(self.branch, origin.refs.main)
            repo.heads.main.set_tracking_branch(origin.refs.main)
            repo.heads.main.checkout(True)
        return repo

    @run_in_exc
    def create_remote_and_fetch(self, repo):
        with contextlib.suppress(Exception):
            repo.create_remote("upstream", self.repo)
        ups_rem = repo.remote("upstream")
        ups_rem.fetch(self.branch)
        return ups_rem

    async def update_locally(
        self, ups_rem, repo, msg=None, Altruix=None, no_restart=False
    ):
        if not Altruix:
            from Main import Altruix
        if msg:
            await msg.edit_msg("UPDATING_LOCALLY")
        try:
            ups_rem.pull(self.branch)
        except GitCommandError:
            repo.git.reset("--hard", "FETCH_HEAD")
        if not no_restart:
            await Altruix.run_cmd_async(
                "pip3 install --no-cache-dir -r requirements.txt"
            )
            await Altruix._restart(soft=False, last_msg=msg, power_hard=True)

    async def update_remotely_heroku(self, ups_rem, repo, msg):
        await msg.edit_msg("HARD_UPDATE_IN_PROGRESS")
        ups_rem.fetch(self.branch)
        repo.git.reset("--hard", "FETCH_HEAD")
        if "heroku" in repo.remotes:
            remote = repo.remote("heroku")
            remote.set_url(self.app_url)
        else:
            remote = repo.create_remote("heroku", self.app_url)
        try:
            remote.push(refspec="HEAD:refs/heads/main", force=True)
        except Exception as error:
            await msg.edit_msg("UPDATER_ERROR", string_args=(error))
            return repo.__del__()
