import requests
import json
from requests.auth import HTTPBasicAuth
import urllib3
import csv
import os

urllib3.disable_warnings()

# Configuration
ISE_HOST = 'https://IP:PORT'  # Replace with your ISE IP or hostname
USERNAME = 'username'                         # ISE API admin username
PASSWORD = 'password'                  # ISE API admin password
VERIFY_SSL = False                         # Set to True if using a valid certificate
PORTAL_ID = "portalid"  # Portal Id if required
# API Endpoint

params = {'size': '50', 'page': 1}

LIST_OF_USERS = []
USER_DETAILS = []
ERROR_USERS = []

# Headers
HEADERS = {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}


def generate_guest_user_xml(guest_users):
    print("Generating XML...")
    # XML header and namespaces
    xml_header = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
    <ns4:guestUserBulkRequest operationType="create" resourceMediaType="vnd.com.cisco.ise.identity.guestuser.2.0+xml" xmlns:ns6="sxp.ers.ise.cisco.com" xmlns:ns5="trustsec.ers.ise.cisco.com" xmlns:ns8="network.ers.ise.cisco.com" xmlns:ns7="anc.ers.ise.cisco.com" xmlns:ers="ers.ise.cisco.com" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:ns4="identity.ers.ise.cisco.com">
    <ns4:resourcesList>"""

    # Iterate through the list of guest users to build the XML for each
    guest_user_xml = ""
    for guest_user_data in guest_users:
        guest_user = guest_user_data["GuestUser"]
        # if not guest_user["sponsorUserName"]:
        #     print(guest_user)
        # Construct the guest user XML part
        sponsorUserName = "usercaptiveportal"
        sponsorUserId = "sponsorUserId"

        if "sponsorUserName" not in guest_user:
            guest_user["sponsorUserName"] = sponsorUserName
        if "sponsorUserId" not in guest_user:
            guest_user["sponsorUserId"] = sponsorUserId
        guest_user_entry = f"""
        <ns4:guestuser id="{guest_user['id']}" name="{guest_user['name']}">
        """

        # Check if 'customFields' exists and is non-empty
        if "customFields" in guest_user and guest_user["customFields"]:
            guest_user_entry += """
            <customFields>
        """
            # Loop through each entry in customFields and add them to the XML
            for key, value in guest_user["customFields"].items():
                guest_user_entry += f"""
                <entry>
                    <key>{key}</key>
                    <value>{value}</value>
                </entry>
                """
            guest_user_entry += """
            </customFields>
        """
        else:
            guest_user_entry += """
            <customFields>
            </customFields>"""
        # Add other guest user information to the XML
        guest_user_entry += f"""
            <guestAccessInfo>
                <fromDate>{guest_user['guestAccessInfo']['fromDate']}</fromDate>
                <location>{guest_user['guestAccessInfo']['location']}</location>
                <toDate>{guest_user['guestAccessInfo']['toDate']}</toDate>
                <validDays>{guest_user['guestAccessInfo']['validDays']}</validDays>
            </guestAccessInfo>
            <guestInfo>
                <enabled>{str(guest_user['guestInfo']['enabled']).lower()}</enabled>
                <smsServiceProvider>Global Default</smsServiceProvider>
                <userName>{guest_user['guestInfo']['userName']}</userName>
            </guestInfo>
            <guestType>{guest_user['guestType']}</guestType>
            <portalId>{guest_user['portalId']}</portalId>
            <sponsorUserName>{guest_user['sponsorUserName']}</sponsorUserName>
        </ns4:guestuser>
        """
        guest_user_xml += guest_user_entry
        # Closing XML tags
    xml_footer = """
    </ns4:resourcesList>
    </ns4:guestUserBulkRequest>"""
    # Combine all parts
    full_xml = xml_header + guest_user_xml + xml_footer
    return full_xml

    # Generate the XML


def handle_user_error(user, response):
    print(type(response))
    print(response["ERSResponse"]["messages"][0]["title"])
    new_error = {
        "username": user["GuestUser"]["name"],
        "message": response["ERSResponse"]["messages"][0]["title"]
    }
    ERROR_USERS.append(new_error)


def write_to_csv():
    with open("error_users.csv", "w", newline='') as csvfile:
        fieldnames = ['username', 'message']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(ERROR_USERS)


def push_user(ise_dst_ip):
    num_of_user = 0
    try:
        num_of_user = int(input("Number of user to push (0: all): "))
        if num_of_user == 0:
            for u in USER_DETAILS:
                # print(
                #     f"Adding '{json.dumps(u, indent=2)}' to https://{ise_dst_ip}")
                ERS_USER_PUSH = f"https://{ise_dst_ip}/ers/config/guestuser"
                response = requests.post(
                    ERS_USER_PUSH,
                    headers=HEADERS,
                    auth=HTTPBasicAuth(USERNAME, PASSWORD),
                    verify=VERIFY_SSL,
                    json=u
                )
                if response.status_code == 201:
                    print(f'User {u["GuestUser"]["name"]} added!')
                else:
                    print(response.text)
                    handle_user_error(u, response.json())
        else:
            for i in range(num_of_user):
                print(USER_DETAILS[i])
                ERS_USER_PUSH = f"https://{ise_dst_ip}/ers/config/guestuser"
                response = requests.post(
                    ERS_USER_PUSH,
                    headers=HEADERS,
                    auth=HTTPBasicAuth(USERNAME, PASSWORD),
                    verify=VERIFY_SSL,
                    json=USER_DETAILS[i]
                )
                if response.status_code == 201:
                    print(
                        f'User {USER_DETAILS[i]["GuestUser"]["name"]} added!')
                else:
                    handle_user_error(USER_DETAILS[i], response.json())

            del USER_DETAILS[:num_of_user]

        if len(ERROR_USERS) > 0:
            print("Writing error to file...")
            write_to_csv()
    except Exception as e:
        print(f"Error on Push User - Exception occurred: {e}")


def get_user_detail(ise_src_ip):
    try:
        for u in LIST_OF_USERS:
            print(f"Getting data for user: {u}")
            ERS_USER_DETAIL = f"https://{ise_src_ip}/ers/config/guestuser/name/{u}"
            response = requests.get(
                ERS_USER_DETAIL,
                headers=HEADERS,
                auth=HTTPBasicAuth(USERNAME, PASSWORD),
                verify=VERIFY_SSL
            )
            if response.status_code == 200:
                data = response.json()
                guestUser = data["GuestUser"]
                if guestUser["status"].lower() != "expired":

                    if '@' in guestUser["guestInfo"]["userName"]:
                        print(guestUser["guestInfo"]["userName"])
                        name = guestUser["guestInfo"]["userName"].split('@')[0]
                        if '_' in name:
                            firstName = name.split('_')[0]
                            lastName = name.split('_')[1]
                        else:
                            firstName = name
                            lastName = "bca.co.id"
                    else:
                        firstName = guestUser["guestInfo"]["userName"]
                        lastName = "bca.co.id"
                    guestUser["portalId"] = "a25ae040-e0e7-11e5-9151-005056bf7f51"
                    # if "sponsorUserName" not in data["GuestUser"]:
                    #     data["GuestUser"]["sponsorUserName"] = "usercaptiveportal"
                    if "sponsorUserName" not in guestUser:
                        guestUser["sponsorUserName"] = "usercaptiveportal"
                    if "sponsorUserId" not in guestUser:
                        guestUser["sponsorUserId"] = "33760f42-aa55-11ec-a360-22f2454f90c5"
                    if "firstName" not in guestUser["guestInfo"]:
                        guestUser["guestInfo"]["firstName"] = firstName
                    if 'lastName' not in guestUser["guestInfo"]:
                        guestUser["guestInfo"]["lastName"] = lastName
                    else:
                        guestUser["sponsorUserName"] = "usercaptiveportal"
                        guestUser["sponsorUserId"] = "33760f42-aa55-11ec-a360-22f2454f90c5"
                    # if 'emailAddress' not in guestUser["guestInfo"]:
                    #     guestUser["guestInfo"]["emailAddress"] = f"***@bca.co.id"
                    if 'company' not in guestUser["guestInfo"]:
                        guestUser["guestInfo"]["company"] = "***"
                    if guestUser["customFields"] == {}:
                        customFields = {
                            "ui_no_hpextension_no_text_label": "***",
                            "ui_floor_text_label": "***",
                        }
                        guestUser["customFields"] = customFields
                    del guestUser["guestInfo"]["password"]
                    # print(json.dumps(data, indent=2))
                    USER_DETAILS.append(data)
                else:
                    print(
                        f"User {guestUser['guestInfo']['userName']} is EXPIRED, skipping!")

    except Exception as e:
        print(f"Error on Get User Detail - Exception occurred: {e}")


def get_users(ise_src_ip):
    total = 1
    user_count = 0
    params["page"] = 1
    ERS_BASE = f"https://{ise_src_ip}/ers/config/guestuser"
    try:
        while total > 0 and params["page"] == 1:
            response = requests.get(
                ERS_BASE,
                params=params,
                headers=HEADERS,
                auth=HTTPBasicAuth(USERNAME, PASSWORD),
                verify=VERIFY_SSL
            )
            if response.status_code == 200:
                total = int(response.json()["SearchResult"]["total"])
                print("total from req: ", total)
                user_count += total
                params["page"] += 1
                data = response.json()["SearchResult"]["resources"]
                for d in data:
                    LIST_OF_USERS.append(d["name"])
            # for user in data:
            #     LIST_OF_USERS.append(user["name"])
            else:
                print(f"Error: {response.status_code} - {response.text}")

        print(LIST_OF_USERS)
        print("Total user collected: ", len(LIST_OF_USERS))
        return 0

    except Exception as e:
        print(f"Error on Get Users - Exception occurred: {e}")
        return 1


if __name__ == '__main__':
    choice = 0
    while choice != 3:
        print("----- Migrate ISE Guest User -----")
        print("1. Get All User Data")
        print("2. Migrate User to new ISE")
        print("3. Exit")
        choice = int(input("> "))
        if choice == 1:
            ise_source = str(
                input("Input ISE source IP and Port (10.0.0.1:9006): "))
            print("Collecting username...")
            get_res = get_users(ise_source)
            if get_res == 0:
                print("Collecting user detail...")
                get_user_detail(ise_source)
                with open('demo_user.json', 'w') as f:
                    json.dump(USER_DETAILS, f, indent=4)
            else:
                print("Error occured!")
                os._exit(1)
        elif choice == 2:
            ise_dst = input("Input ISE source IP and Port (10.0.0.1:9006): ")
            push_user(ise_dst)
        else:
            os._exit(1)
    # with open('./users_detail.json', 'w') as f:
    #     json.dump(USER_DETAILS, f, indent=4)
    # xml = generate_guest_user_xml(USER_DETAILS)
    # with open('./userxml.xml', 'w') as f:
    #     f.write(xml)
    # print(xml)
