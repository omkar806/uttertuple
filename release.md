# Preparing for new release

This document outlines the steps to prepare for a new release of the project.
## Step 1: Make the main branch ready for release
Before creating a new release, ensure that the `main` branch is up-to-date and all tests are passing. Run the following command to execute the test suite:

```bash
make tests
```

If any tests fail, address the issues before proceeding.

## Step 2: Create a tag for the new release
Once the `main` branch is ready, create a new tag for the release. Use semantic versioning (e.g., `v1.0.0`). You can create a new tag using the following command:
```bash
git tag v1.0.0
```
Replace `v1.0.0` with the appropriate version number for your release.


## Step 3: Push the tag to the remote repository
After creating the tag, push it to the remote repository using the following command:
```bash
git push origin v1.0.0
```
Replace `v1.0.0` with the version number you used in the previous step


## Step 4: Create a release in the repository
Go to the repository's releases page on GitHub or your Git hosting service. Click on "Draft a new release" and fill in the details:
- Tag version: Select the tag you just pushed.
- Release title: Provide a title for the release.
- Description: Add a description of the changes included in this release. You can use the changelog or summarize the key features and fixes.    

Once you have filled in the details, click on "Publish release" to make it official.


## Step 5: Merge the release branch back into uat or prod branch
If you are using a branching strategy that includes `uat` or `prod` branches, merge the `main` branch into the appropriate branch. For example, to merge into the `uat` branch, use the following commands:
```bash
git checkout uat
git merge main
git push origin uat
```
Repeat the process for the `prod` branch if necessary.
```bash
git checkout prod
git merge main
git push origin prod
```
Replace `uat` and `prod` with the actual names of your branches if they differ.

## Step 6: Notify the team
Once the release is published, notify the team about the new release. You can do this via email, chat, or any other communication channel your team uses. Include the release notes and any important information about the deployment process if applicable.