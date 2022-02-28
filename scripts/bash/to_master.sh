

deploy_branch=$(git rev-parse --abbrev-ref HEAD)


if [ "$deploy_branch" == "master" ]
 then
  echo Current branch is master. No deployment required.
  exit 0
fi


message=$(git status | tail -n 1)

if [ "$message" != "nothing added to commit but untracked files present (use \"git add\" to track)" ] \
   && [ "$message" != "nothing to commit, working tree clean" ]
 then
  echo You don\'t have a clean working state. Make sure, to commit your changes first.
  exit 1
fi


echo Working directoy clean. Proceeding with merge to master.


git checkout master

git pull origin master


if [ $? -ne 0 ]
 then
  exit $?
fi


git merge $deploy_branch


echo if the merge did not produce any conflict, you should push the merge:
echo git push origin master
echo And afterwards you should switch back to your development branch \($deploy_branch\):
echo git checkout $deploy_branch
