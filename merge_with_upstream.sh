#!/bin/bash -e
git checkout "$1"
git remote add upstream git@github.com:UWVerse/uwconnect-backend.git || true
git fetch upstream
git merge upstream/"$1" --no-edit
git push
