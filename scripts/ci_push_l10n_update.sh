#!/bin/bash
# Meant to be run via CI, this handles checking if ci_update_l10n_template.py
# actually made any changes and, if so, pushing them to the weblate-in branch
# (as well as rebasing and force-pushing that branch)

# Fail the CI on any errors down below
set -e

if [[ $(git status --porcelain) ]]
then
    echo "Changes to template.pot detected, pushing to weblate-in"
    git stash
    git switch weblate-in
    git rebase origin/dev
    git stash pop
    # First -m is title, second -m is body
    git commit -a -m "Update template.pot" -m "Corresponds to ${GITHUB_SHA}."
    git push --force-with-lease origin weblate-in
else
    echo "No changes to template.pot, skipping commit"
fi
