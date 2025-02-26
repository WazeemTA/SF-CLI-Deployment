import os
import subprocess

# Define the metadata mapping for Salesforce components
# https://github.com/forcedotcom/source-deploy-retrieve/blob/main/src/registry/metadataRegistry.json - this git repo contains all the metadata Registry, add additional metadatas as required for different clouds
metadata_map = {
    # Apex Code and Automation
    ".cls": "ApexClass",
    ".trigger": "ApexTrigger",
    ".component": "ApexComponent",
    ".page": "ApexPage",
    ".flow-meta.xml": "Flow",
    ".flowDefinition-meta.xml": "FlowDefinition",

    # Customization and Schema
    ".object-meta.xml": "CustomObject",
    ".field-meta.xml": "CustomField",
    ".tab-meta.xml": "CustomTab",
    ".labels-meta.xml": "CustomLabels",
    ".md-meta.xml": "CustomMetadata",
    ".recordType-meta.xml": "RecordType",
    ".validationRule-meta.xml": "ValidationRule",
    ".webLink-meta.xml": "WebLink",
    ".compactLayout-meta.xml": "CompactLayout",
    ".fieldSet-meta.xml": "FieldSet",
    ".loyaltyProgramSetup-meta.xml": "LoyaltyProgramSetup",

    # UI Components
    ".layout-meta.xml": "Layout",
    ".listView-meta.xml": "ListView",
    ".app-meta.xml": "CustomApplication",
    ".appMenu-meta.xml": "AppMenu",
    ".flexipage-meta.xml": "FlexiPage",
    ".component-meta.xml": "ApexComponent",

    # Permissions and Security
    ".permissionset-meta.xml": "PermissionSet",
    ".profile-meta.xml": "Profile",
    ".customPermission-meta.xml": "CustomPermission",
    ".sharingRules-meta.xml": "SharingRules",

    # Automation and Business Processes
    ".approvalProcess-meta.xml": "ApprovalProcess",
    ".workflow-meta.xml": "WorkflowRule",
    ".emailAlert-meta.xml": "EmailAlert",
    ".processBuilder-meta.xml": "ProcessBuilder",
    ".assignmentRules-meta.xml": "AssignmentRules",
    ".escalationRules-meta.xml": "EscalationRules",
    ".autoResponseRules-meta.xml": "AutoResponseRules",

    # Email and Communication
    ".email-meta.xml": "EmailTemplate",
    ".email": "EmailTemplate",
    ".letterhead-meta.xml": "Letterhead",
    ".emailServicesFunction-meta.xml": "EmailServicesFunction",
    ".emailFolder-meta.xml": "EmailFolder",

    # Reports and Dashboards
    ".report-meta.xml": "Report",
    ".reportFolder-meta.xml": "ReportFolder",
    ".dashboard-meta.xml": "Dashboard",
    ".dashboardFolder-meta.xml": "DashboardFolder",
    ".reportType-meta.xml": "ReportType",

    # Integration and API
    ".namedCredential-meta.xml": "NamedCredential",
    ".externalDataSource-meta.xml": "ExternalDataSource",
    ".remoteSiteSetting-meta.xml": "RemoteSiteSetting",
    ".connectedApp-meta.xml": "ConnectedApp",

    # Data and Development Utilities
    ".application-meta.xml": "CustomApplication",
    ".resource-meta.xml": "StaticResource",
    ".document-meta.xml": "Document",
    ".documentFolder-meta.xml": "DocumentFolder",

    # Einstein and Advanced Features
    ".waveApplication-meta.xml": "WaveApplication",
    ".waveDashboard-meta.xml": "WaveDashboard",
    ".waveDataset-meta.xml": "WaveDataset",
    ".waveLens-meta.xml": "WaveLens",
    ".waveFolder-meta.xml": "WaveFolder",

    # Others
    ".decisionTable-meta.xml": "DecisionTable",
    ".decisionTableDatasetLink-meta.xml": "DecisionTableDatasetLink",
    ".quickAction-meta.xml": "QuickAction",
    ".globalValueSet-meta.xml": "GlobalValueSet",
    ".translation-meta.xml": "Translations",
    ".homePageLayout-meta.xml": "HomePageLayout",
    ".batchCalcJobDefinition-meta.xml": "BatchCalcJobDefinition"
}

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

# Function to group components by metadata type
def group_components_by_type(file_list):
    metadata_dict = {}
    for file in file_list:
        for key, metadata_type in metadata_map.items():
            if file.endswith(key):
                # Dynamically remove the file extension (key) from the file name
                component_name = os.path.basename(file).replace(key, "")

                # For object-scoped metadata (like CustomField, ValidationRule), prefix with object name
                if metadata_type in ["CustomField", "ValidationRule", "ListView", "CompactLayout"]:
                    object_name = os.path.basename(os.path.dirname(os.path.dirname(file)))  # Extract Object API Name
                    component_name = f"{object_name}.{component_name}"

                # For directory-scoped metadata (like Reports, EmailTemplates), include the parent directory
                elif metadata_type in ["Report", "EmailTemplate", "Dashboard"]:
                    parent_dir = os.path.basename(os.path.dirname(file))  # Extract the immediate parent directory
                    component_name = f"{parent_dir}/{component_name}"

                # Store components under their respective metadata type
                metadata_dict.setdefault(metadata_type, []).append(component_name)
                break  # Stop searching once a match is found

    return metadata_dict


# Function to generate a manifest file
def generate_manifest(metadata_dict, output_dir, manifest_name):
    # Build the CLI command with multiple --metadata flags
    metadata_flags = []
    
    for metadata_type, components in metadata_dict.items():
        for item in components:
            item = item.strip().rstrip("\\")  # Remove unwanted trailing slashes
            metadata_flags.append(f'--metadata \"{metadata_type}:{item}\"')

    command = [
        "powershell", "-Command",
        f"sf project generate manifest {' '.join(metadata_flags)} --name {manifest_name}"
    ]

    try:
        # Run the command in the specified output directory
        subprocess.run(command, cwd=output_dir, check=True, text=True)
        print(f"Manifest generated successfully at {output_dir}/{manifest_name}.xml")
    except subprocess.CalledProcessError as e:
        print(f"Error generating manifest: {e.stderr}")

# Main script
if __name__ == "__main__":
    current_branch = get_current_branch()
    print(f"Using current branch: {current_branch}")

    # Prompt the user for the component file name
    custom_file_name = input("Do you want to provide a custom component file name? (y/n): ").strip().lower()
    if custom_file_name == "y":
        file_base_name = input("Enter the custom base name for the component file & Manifest File: ").strip()
        comp_file_name = f"{file_base_name}CompFile.txt"
        manifest_name = f"{file_base_name}Manifest"
    else:
        comp_file_name = f"{current_branch}CompFile.txt"
        manifest_name = f"{current_branch}Manifest"

    # Construct the file path to the component list file
    file_list_path = os.path.join("manifest", current_branch, comp_file_name)
    if not os.path.exists(file_list_path):
        print(f"Error: File not found at {file_list_path}")
        exit(1)

    try:
        with open(file_list_path, "r") as file:
            file_list = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print(f"Error: File not found at {file_list_path}")
        exit(1)

    # Define the output directory for the manifest
    output_dir = os.path.join("manifest", current_branch)
    os.makedirs(output_dir, exist_ok=True)

    # Group components by metadata type
    metadata_dict = group_components_by_type(file_list)

    # Log grouped components
    print("\nGrouped components by metadata type:")
    for metadata_type, files in metadata_dict.items():
        print(f"{metadata_type}: {len(files)} component(s)")
        for file in files:
            print(f"  - {file}")

    # Generate the manifest file
    generate_manifest(metadata_dict, output_dir, manifest_name)