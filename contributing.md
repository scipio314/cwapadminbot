# How To Contribute

Open sourced projects live from the generous help by contributors that sacrifice their time. Below you will find instructions on how to contribute your Python code to the project. If you are unfamiliar with git and want to get a general understanding of it, you can watch this [15 minute overview.](https://www.youtube.com/watch?v=USjZcfj8yxE) In short it is a version control system meant to keep track of changes made by multiple people. The instructions below are pretty formal, but don't be afraid to make a mistake, we will both figure it out along the way.

## Setting things up

1. Fork the `cwapadminbot` repository to your Github account.
2. Clone your forked repository of `cwapadminbot` to your computer:

    1. Create a folder to work out of. For me I have a Github folder in my documents on my C drive.

    ```bash
    $ cd documents/github
    $ git clone https://github.com/scipio314/cwapadminbot
    $ cd cwapadminbot
    ```

3. Add a track to the original repository:

    ```bash
    $ git remote add upstream https://github.com/scipio314/cwapadminbot
    ```
    This makes it so you receive changes from the main repository and not your forked one.

4. Install dependencies:

    ```bash
    $ pip install -r requirements.txt -r requirements-dev.txt
    ```

You now have a copy of `cwapadminbot` on your machine with all the requirements installed.

## Finding something to do

If you already know what you'd like to work on, you can skip this section.

If you have an idea for soemthing to do, first check if it's been filed on the issue tracker. If so, add a comment to the issue saying you'd like to work on it.

## Instructions for making a code change

The central development branch is `master`, which should be clean and ready for release at any time. In general all changes should be done as feature branches based off `master`.

Here is how to make a one-off code change.

1. **Choose a descripitve branch name.** It should be lower case, hyphen seperated, and a noun describing the change (so, `welcome-message`, but not `implement-welcome-message`). Also, it shouldn't start with `hotfix` or `release`.

2. **Create a new branch with this name, starting from `master`**. In other words, run:

    ```bash
    $ git fetch upstream
    $ git checkout master
    $ git merge upstream/master
    $ git checkout -b your-branch-name
    ```

3. **Make a commit to your feature branch.** Each commit should be self-contained and have descriptive commit message that helps other developers understand why changes were made.

   * Refer to relevent issues in the commit by writing "#105".
   * Your code should adhere to the PEP 8 Style Guide, with the exception that maximum line length of 120.
   * Document your code. This code uses [Google style docstrings](http://google.github.io/styleguide/pyguide.html). Add a description on what your function does, what each argument is, and the default values for optional arguments. Provide examples as much as possible.
   * Add yourself to the [authors.md](authors.md) file in an alphabetical fashion.
   * Finally, push to your fork:

    ```bash
    $ git push origin your-branch-name
    ```

4. **When your code is ready to merge, create a pull request.**

* Go to your fork on Github, select your branch from the dropdown menu, and click "New pull request".
* Add a descriptive comment explaining the purpose of the branch. This lets a reviewer know what the purpose of this is.
* Click "Create pull request". Someone will review your code.

5. **Address review comments**

* When someone has reviewed the code, you will have to respond in two ways:
  * Make a new commit addressing the comments you agree with, and push it to the same branch.
  * Reply to each comment. Either respond with "Done" or an explanation why something isn't implemented.
* Resolve any new merge conflicts:

    ```bash
    $ git checkout your-branch-name
    $ git fetch upstream
    $ git merge upstream/master
    $ ...[fix the conflicts]...
    $ git commit -a
    $ git push origin your-branch-name
    ```

* At the end, the reviewer will merge the pull request.

6. **Tidy up!** Delete the feature branch from both your local machine and your online repository:

    ```bash
    $ git branch -D your-branch-name
    $ git push origin --delete your-branch-name
    ```

7. **Celebrate.** Congratulations, you've contributed to `cwapadminbot`! The above was a very long and formal explanation. The process doesn't have to be perfect. Mistakes will be made along the way and that is fine.
