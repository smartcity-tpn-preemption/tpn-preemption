#!/bin/bash

git gc
git pull origin master
git add .
git commit -a -m "new .json files were added"
git push origin master
