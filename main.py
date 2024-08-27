import grpc
import re
from dotenv import load_dotenv
from pathlib import Path
from thefuzz import process
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

def choose_type(client, metadata) -> str:
    req = commands__pb2.Rpc.Object.Search.Request()
    all_objects = client.ObjectSearchWithMeta(req, metadata=metadata)

    available_types = [
        result for result in all_objects.results
        if result.details.fields.get('layout') and result.details.fields['layout'].number_value == 4
    ]

    options = [
        f"{index}: {type.details.fields['name'].string_value}" 
        for index, type in enumerate(available_types)
    ]

    completer = FuzzyWordCompleter(options, WORD=True)
    user_input = prompt("Select a type: ", completer=completer)
    selected_option, _ = process.extractOne(user_input, options)
    chosen_type_index = options.index(selected_option)
    chosen_type = available_types[chosen_type_index]

    type_id = chosen_type.details.fields['uniqueKey'].string_value
    with open('.env', 'a') as file:
        file.write(f'TYPE_ID={type_id}\n')

    return type_id

def create_object_with_content(client, metadata, content):
    load_dotenv()
    type_id = os.getenv('TYPE_ID')

    if type_id is None:
        type_id = choose_type(client, metadata)

    req = commands__pb2.Rpc.Object.Search.Request()
    all_objects = client.ObjectSearchWithMeta(req, metadata=metadata)

    chosen_type = next(
        (result for result in all_objects.results if result.details.fields.get('uniqueKey') and result.details.fields['uniqueKey'].string_value == type_id),
        None
    )

    req = commands__pb2.Rpc.Object.Create.Request(
        objectTypeUniqueKey = chosen_type.details.fields['uniqueKey'].string_value,
        spaceId = chosen_type.details.fields['spaceId'].string_value,
        templateId = chosen_type.details.fields['defaultTemplateID'].string_value
    )
    created_object = client.ObjectCreate(req, metadata=metadata)

    new_block = Block(
        id = "",
        text = Block.Content.Text(text=content)
    )
    req = commands__pb2.Rpc.Block.Create.Request(
        contextId = created_object.objectId,
        block = new_block
    )
    client.BlockCreate(req, metadata=metadata)

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

        objects_with_links.add(obj.details.fields['objectId'].string_value)
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

        objects_with_links.add(obj.details.fields['objectId'].string_value)
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
