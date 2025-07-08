import os
import xml.etree.ElementTree as ET
import subprocess
import sys
import json
import pandas as pd
import re

# Hardcoded values for source and target orgs (can be changed as needed)
DEFAULT_SOURCE_ORG = "waz.sourceorg"
DEFAULT_TARGET_ORG = "waz.targorg"

def get_user_input(prompt, default_value):
    user_input = input(f"{prompt} (Press Enter to use '{default_value}'):")
    return user_input.strip() if user_input else default_value

def fetch_manifest():
    branch_name = subprocess.getoutput("git rev-parse --abbrev-ref HEAD")
    manifest_base_name = get_user_input("Enter manifest base name", branch_name)
    manifest_name = f"{manifest_base_name}Manifest.xml"
    manifest_path = os.path.join("manifest", branch_name, manifest_name)
    return manifest_path, branch_name, manifest_name

def run_sf_command(command):
    """Runs an sf CLI command and prints output for debugging."""
    print(f"Running command: {' '.join(command)}")  # Debugging
    try:
        result = subprocess.run(command, capture_output=True, text=True, shell=sys.platform == "win32", encoding="utf-8")
        print(result.stdout)  # Show output
        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            exit(1)  # Exit if the command fails
        return result.stdout
    except Exception as e:
        print(f"Exception occurred: {e}")
        exit(1)

def retrieve_package(source_org, manifest_path):
    retrieve = get_user_input("Do you want to retrieve the package from the source org? (y/n)", "n").lower()
    if retrieve == "y":
        run_sf_command(["sf", "project", "retrieve", "start", "--manifest", manifest_path, "--target-org", source_org])

def extract_test_classes(manifest_path):
    tree = ET.parse(manifest_path)
    root = tree.getroot()
    namespace = "{http://soap.sforce.com/2006/04/metadata}"
    test_classes = [member.text for types in root.findall(f"{namespace}types")
                    if types.find(f"{namespace}name").text == "ApexClass"
                    for member in types.findall(f"{namespace}members")
                    if "Test" in member.text]
    return test_classes

def validate_deployment(target_org, manifest_path, test_classes):
    start_validation = get_user_input("Do you want to start validation? (y/n)", "y").lower()
    if start_validation != "y":
        print("Validation skipped.")
        return None, None

    command = [
        "sf", "project", "deploy", "start", "--dry-run", "--manifest", manifest_path, "--target-org", target_org,
        "--test-level", "RunSpecifiedTests" if test_classes else "NoTestRun"
    ]
    if test_classes:
        command.extend(["--tests", *test_classes])

    validation_result = run_sf_command(command)
    
    deploy_id = None
    for line in validation_result.split("\n"):
        if "Deploy ID" in line:
            deploy_id = line.split(":")[-1].strip()
            break
    
    return deploy_id

def deploy(target_org, manifest_path, job_id, manifest_name):
    deploy_id = None
    if job_id:
        if get_user_input("Validation successful. Do you want to deploy? (y/n)", "n").lower() == "y":
            output = run_sf_command(["sf", "project", "deploy", "start", "--manifest", manifest_path, "--target-org", target_org, "--json"])
            try:
                result_json = json.loads(output)
                deploy_id = result_json["result"].get("id")
            except json.JSONDecodeError:
                print("⚠️ Failed to parse JSON response.")
    else:
        if get_user_input("Validation failed. Do you want to force deploy? (y/n)", "n").lower() == "y":
            output = run_sf_command(["sf", "project", "deploy", "start", "--manifest", manifest_path, "--target-org", target_org, "--json"])
            try:
                result_json = json.loads(output)
                deploy_id = result_json["result"].get("id")
            except json.JSONDecodeError:
                print("⚠️ Failed to parse JSON response.")
    
    if deploy_id:
        post_deployment_report(deploy_id, target_org, manifest_name, manifest_path)

def post_deployment_report(job_id, target_org, manifest_name, manifest_path):
    if not job_id:
        print("Skipping deployment report as job ID is not available.")
        return
    
    command = f"sf project deploy report --job-id {job_id} --target-org {target_org} --json"
    try:
        result = subprocess.run(command, capture_output=True, text=True, shell=True, check=True)
        report_data = json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print("⚠️ Error running Salesforce CLI:", e)
        return
    except json.JSONDecodeError:
        print("⚠️ Failed to parse JSON response.")
        return
    
    deployment_details = parse_deployment_report(report_data)
    if deployment_details:
        update_excel(manifest_name, manifest_path, deployment_details)

def parse_deployment_report(report_data):
    if not report_data or "result" not in report_data:
        return None
    
    result = report_data["result"]
    components = []
    if "details" in result and "componentSuccesses" in result["details"]:
        for comp in result["details"]["componentSuccesses"]:
            component_name = comp.get("fullName", "Unknown")
            component_type = comp.get("componentType", "Unknown")
            components.append(f"{component_type}: {component_name}" if component_type else component_name)
    
    return {
        "status": result.get("status", "Unknown"),
        "completedDate": result.get("completedDate", "N/A"),
        "components": ", ".join(components) if components else "No components deployed"
    }

def update_excel(manifest_name, manifest_path, deployment_details):
    file_path = "DeploymentSheet.xlsx"
    new_data = pd.DataFrame([{
        "Package File Name": manifest_name,
        "Package Path": manifest_path,
        "Deployment Status": deployment_details["status"],
        "Deployment Date": deployment_details["completedDate"],
        "Components Deployed": deployment_details["components"]
    }])
    if os.path.exists(file_path):
        existing_data = pd.read_excel(file_path)
        df_final = pd.concat([existing_data, new_data], ignore_index=True)
    else:
        df_final = new_data
    df_final.to_excel(file_path, index=False)
    print("✅ Deployment details saved to DeploymentSheet.xlsx")

def main():
    source_org = get_user_input("Enter source org", DEFAULT_SOURCE_ORG)
    target_org = get_user_input("Enter target org", DEFAULT_TARGET_ORG)
    manifest_path, branch_name, manifest_name = fetch_manifest()
    retrieve_package(source_org, manifest_path)
    test_classes = extract_test_classes(manifest_path)
    job_id = validate_deployment(target_org, manifest_path, test_classes)
    deploy(target_org, manifest_path, job_id, manifest_name)

if __name__ == "__main__":
    main()
