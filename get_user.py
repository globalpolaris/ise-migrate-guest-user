import requests
import json
from requests.auth import HTTPBasicAuth
import urllib3
import dicttoxml
import xml.dom.minidom

urllib3.disable_warnings()

# Configuration
ISE_HOST = 'https://IP_ISE:9060'  # Replace with your ISE IP or hostname
USERNAME = 'username'                         # ISE admin username
PASSWORD = 'Passowrd'                  # ISE admin password
VERIFY_SSL = False                         # Set to True if using a valid certificate
PORTAL_ID = "a25ae040-e0e7-11e5-9151-005056bf7f51"  # Portal Id if required
# API Endpoint
ERS_BASE = f"{ISE_HOST}/ers/config/guestuser"
USERS_ENDPOINT = f"{ERS_BASE}/internaluser"
params = {'size': '100', 'page': 1}

LIST_OF_USERS = []
USER_DETAILS = []

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


def get_user_detail():
    try:
        for u in LIST_OF_USERS:
            ERS_USER_DETAIL = f"{ISE_HOST}/ers/config/guestuser/name/{u}"
            response = requests.get(
                ERS_USER_DETAIL,
                headers=HEADERS,
                auth=HTTPBasicAuth(USERNAME, PASSWORD),
                verify=VERIFY_SSL
            )
            if response.status_code == 200:
                data = response.json()
                data["GuestUser"]["portalId"] = "a25ae040-e0e7-11e5-9151-005056bf7f51"
                del data["GuestUser"]["guestInfo"]["password"]
                print(json.dumps(data, indent=2))
                USER_DETAILS.append(data)
    except Exception as e:
        print(f"Exception occurred: {e}")


def get_users():
    total = 1
    user_count = 0
    try:
        # print(data)
        while total > 0 and params["page"] <= 1:
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
                print(user_count)
            # for user in data:
            #     LIST_OF_USERS.append(user["name"])
        else:
            print(f"Error: {response.status_code} - {response.text}")

        print(LIST_OF_USERS)
        print("Total user collected: ", len(LIST_OF_USERS))

    except Exception as e:
        print(f"Exception occurred: {e}")


if __name__ == '__main__':
    get_users()
    get_user_detail()
    # with open('./users_detail.json', 'w') as f:
    #     json.dump(USER_DETAILS, f, indent=4)
    xml = generate_guest_user_xml(USER_DETAILS)
    with open('./userxml.xml', 'w') as f:
        f.write(xml)
    print(xml)
