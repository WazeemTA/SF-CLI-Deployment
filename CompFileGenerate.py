import os
import subprocess

# Function to get the current branch name
def get_current_branch():
    try:
        return subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True
        ).stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting current branch: {e.stderr}")
        exit(1)

# Function to stash changes for the current branch
def stash_changes():
    try:
        current_branch = get_current_branch()
        stash_message = f"stash-for-{current_branch}"
        subprocess.run(["git", "stash", "push", "-m", stash_message], check=True)
        print(f"Stashed changes with message: {stash_message}")
    except subprocess.CalledProcessError as e:
        print(f"Error stashing changes: {e.stderr}")

# Function to apply stash for the current branch
def apply_stash():
    try:
        current_branch = get_current_branch()
        stash_list = subprocess.run(
            ["git", "stash", "list"],
            capture_output=True, text=True, check=True
        ).stdout.strip()

        stash_id = None
        for line in stash_list.splitlines():
            if f"stash-for-{current_branch}" in line:
                stash_id = line.split(":")[0]
                break

        if stash_id:
            subprocess.run(["git", "stash", "apply", stash_id], check=True)
            print(f"Applied stash: {stash_id}")
        else:
            print(f"No stash found for branch: {current_branch}")
    except subprocess.CalledProcessError as e:
        print(f"Error applying stash: {e.stderr}")

# Function to save components to a file
def save_components_to_file(branch, components):
    try:
        # Prompt the user for a custom file name
        custom_name = input("Do you want to provide a custom name for the CompFile? (y/n): ").strip().lower()
        
        if custom_name == "y":
            file_suffix = input("Enter the custom name: ").strip()
            file_name = f"{file_suffix}CompFile.txt"
        else:
            file_name = f"{branch}CompFile.txt"

        # Construct the directory path: current_directory/manifest/<branch_name>
        directory_path = os.path.join(os.getcwd(), "manifest", branch)
        os.makedirs(directory_path, exist_ok=True)

        # Full file path
        file_path = os.path.join(directory_path, file_name)

        # Write the components to the file
        with open(file_path, "w") as f:
            for component in components:
                f.write(component + "\n")

        print(f"Components saved to {file_path}")
    except Exception as e:
        print(f"Error saving components to file: {e}")

# Function to get the files committed to the current branch
def get_committed_files(branch):
    try:
        committed_files = subprocess.run(
            ["git", "diff", "--name-only", "--oneline", f"origin/sflc-release1..{branch}"],
            capture_output=True, text=True, check=True
        ).stdout.strip().splitlines()

        # Filter only the file paths that contain '.xml' or '.cls'
        return [line for line in committed_files if '.xml' in line or '.cls' in line]
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving committed files: {e.stderr}")
        exit(1)

# Main script
if __name__ == "__main__":
    # Ask if the user wants to provide the branch name
    use_provided_branch = input("Do you want to provide the name for the branch? (y/n): ").strip().lower()

    if use_provided_branch == "y":
        # Request user input for the branch name
        branch = input("Enter the branch name: ").strip()
    elif use_provided_branch == "n":
        # Use the current branch name
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True
        ).stdout.strip()
        print(f"Using current branch: {branch}")
    else:
        print("Invalid input. Please enter 'y' or 'n'.")
        exit(1)

    # Confirm the branch name
    print(f"Branch selected: {branch}")

    # Git checkout to the current branch
    try:
        subprocess.run(["git", "checkout", branch], check=True)
        print(f"Checked out to branch: {branch}")
    except subprocess.CalledProcessError as e:
        print(f"Error checking out branch: {e.stderr}")
        exit(1)

    # Get the files committed to the current branch
    committed_files = get_committed_files(branch)

    if committed_files:
        print(f"Retrieved {len(committed_files)} files committed to the branch.")
        save_components_to_file(branch, committed_files)
    else:
        print(f"No committed files found for branch: {branch}")
