import grpc
import re
from dotenv import load_dotenv
from pathlib import Path
from prompt_toolkit import prompt
from prompt_toolkit.completion import FuzzyWordCompleter
import sys
import os

sys.path.insert(0, os.path.abspath('generated_protos_py'))
from get_port import get_anytype_port
from generated_protos_py.service_pb2_grpc import ClientCommandsStub
from generated_protos_py.service_pb2 import commands__pb2
from generated_protos_py.models_pb2 import Block

PURPLE = "\033[95m"
RESET = "\033[0m"

def fetch_app_key(grpc_client):
    req = commands__pb2.Rpc.Account.LocalLink.NewChallenge.Request(appName="Example")
    new_challenge = grpc_client.AccountLocalLinkNewChallenge(req)
    
    print('👋 Seems like it is the first time you are using Anytype Capture, please allow this software access to your vault by entering the token below')
    input_token = input('🔑 Enter the 4-digit token: ')
    
    req = commands__pb2.Rpc.Account.LocalLink.SolveChallenge.Request(
        challengeId=new_challenge.challengeId, 
        answer=input_token)
    solved_challenge = grpc_client.AccountLocalLinkSolveChallenge(req)
    with open('.env', 'a') as file:
        file.write(f'APP_KEY={solved_challenge.appKey}\n')
    return solved_challenge.appKey


def create_authenticated_client():
    port = get_anytype_port()

    grpc_client = ClientCommandsStub(
        grpc.insecure_channel(f'127.0.0.1:{port}')
    )

    load_dotenv()
    app_key = os.getenv('APP_KEY')

    if app_key is None:
        app_key = fetch_app_key(grpc_client)

    req = commands__pb2.Rpc.Wallet.CreateSession.Request(appKey=app_key)
    metadata = [
        ('token', grpc_client.WalletCreateSession(req).token)
    ]
    return grpc_client, metadata

def find_object_by_name(client, metadata, name: str):
    req = commands__pb2.Rpc.Object.SearchWithMeta.Request(fullText=name, returnMeta=True)
    all_objects = client.ObjectSearchWithMeta(req, metadata=metadata)
    for obj in all_objects.results:
        if 'name' in obj.details.fields:
            name_str = obj.details.fields['name'].string_value
            if name_str.lower() == name.lower():
                return obj
    return None

client, metadata = create_authenticated_client()

space_ids = set()
objects_with_links = set()

# First query for [[ ]] patterns
req_brackets = commands__pb2.Rpc.Object.SearchWithMeta.Request(fullText="[[ ]]", returnMeta=True)
all_objects_brackets = client.ObjectSearchWithMeta(req_brackets, metadata=metadata)

with open("results.txt", "w") as file:
    for obj in all_objects_brackets.results:
        targets_and_highlights = []

        # Check for [[ ]] patterns in the metadata highlights
        for m in obj.meta:
            highlight_str = m.highlight
            matches = re.findall(r'#?\[\[(.*?)\]\]', highlight_str)
            if matches:
                for match in matches:
                    target = find_object_by_name(client, metadata, match)
                    if target:
                        target_name = target.details.fields['name'].string_value
                        targets_and_highlights.append((highlight_str, target_name))

        if not targets_and_highlights:
            continue

        objects_with_links.add(obj.details.fields['id'].string_value)
        space_ids.add(obj.details.fields['spaceId'].string_value)

        if 'name' in obj.details.fields:
            name_str = obj.details.fields['name'].string_value
        else:
            name_str = "[UNNAMED OBJECT]"
        
        print(PURPLE + name_str + RESET)
        file.write("\n" + name_str + "\n")

        for highlight_str, target_name in targets_and_highlights:
            print("\t" + highlight_str)
            file.write("\t" + highlight_str + "\n")
            print("-> " + target_name)
            file.write("-> " + target_name + "\n")



# Second query for # links
req_hashes = commands__pb2.Rpc.Object.SearchWithMeta.Request(fullText="#", returnMeta=True)
all_objects_hashes = client.ObjectSearchWithMeta(req_hashes, metadata=metadata)

with open("results.txt", "w") as file:
    for obj in all_objects_hashes.results:
        targets_and_highlights = []

        # Check for # links in the metadata highlights
        for m in obj.meta:
            highlight_str = m.highlight
            matches = re.findall(r'#(\w+)', highlight_str)
            if matches:
                for match in matches:
                    target = find_object_by_name(client, metadata, match)
                    if target:
                        target_name = target.details.fields['name'].string_value
                        targets_and_highlights.append((highlight_str, target_name))

        if not targets_and_highlights:
            continue

        objects_with_links.add(obj.details.fields['id'].string_value)
        space_ids.add(obj.details.fields['spaceId'].string_value)

        if 'name' in obj.details.fields:
            name_str = obj.details.fields['name'].string_value
        else:
            name_str = "[UNNAMED OBJECT]"
        
        print(PURPLE + name_str + RESET)
        file.write("\n" + name_str + "\n")

        for highlight_str, target_name in targets_and_highlights:
            print("\t" + highlight_str)
            file.write("\t" + highlight_str + "\n")
            print("-> " + target_name)
            file.write("-> " + target_name + "\n")
print()
print("Total objects with links found: ", len(objects_with_links))

print()
print(" Spaces where the objects belong:")
for space_id in space_ids:
    print(space_id)
