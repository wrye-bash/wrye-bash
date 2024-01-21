#!/bin/bash
# Only works if run via GitHub Actions. Checks if there are actually any
# template.pot changes from running the update script and, if so, force-pushes
# them to the remote weblate-in branch.

if [[ $(git status --porcelain) ]]
then
    echo "Changes to template.pot detected, pushing to weblate-in"
    # First -m is title, second -m is body
    git commit -a -m "Update template.pot" -m "Corresponds to ${GITHUB_SHA}."
    git push --force-with-lease origin weblate-in
else
    echo "No changes to template.pot, skipping commit"
fi
