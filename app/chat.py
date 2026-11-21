"""Chat with the deployed single-user Study Coach from a terminal."""

import argparse
import sys
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from cloud_client import invoke


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-arn", required=True)
    parser.add_argument("--prompt", help="One-shot prompt; omit for an interactive session")
    args = parser.parse_args()
    parts = args.runtime_arn.split(":")
    if len(parts) != 6 or parts[2] != "bedrock-agentcore" or not parts[5].startswith("runtime/"):
        parser.error("--runtime-arn must be an AgentCore Runtime ARN")
    client = boto3.client("bedrock-agentcore", region_name=parts[3],
                          config=Config(read_timeout=300, retries={"max_attempts": 0}))
    session = str(uuid4())
    started = False
    try:
        if args.prompt:
            started = True
            _, answer = invoke(client, args.runtime_arn, session, args.prompt)
            print(answer)
        else:
            print("AWS Study Coach. Finish your exam before /quit. Completed results are saved.")
            while True:
                try:
                    prompt = input("You: ").strip()
                except EOFError:
                    break
                if prompt.lower() in ("/quit", "/exit"):
                    break
                if not prompt:
                    continue
                started = True
                _, answer = invoke(client, args.runtime_arn, session, prompt)
                print(f"Coach: {answer}\n")
    except KeyboardInterrupt:
        print("\nClosing session.")
    except (ClientError, BotoCoreError, ValueError, AssertionError) as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if started:
            client.stop_runtime_session(agentRuntimeArn=args.runtime_arn, runtimeSessionId=session)
    return 0


if __name__ == "__main__":
    sys.exit(main())
