#!/usr/bin/env python

import boto3
import botocore
from diskcache import Cache
from argparse import ArgumentParser


BOTO3_CONFIG = botocore.config.Config(retries=dict(max_attempts=30))


def parseargs():
    p = ArgumentParser()
    p.add_argument(
        "-c",
        "--cache",
        required=False,
        default="~/.cache/ssm_search",
        help="Cache path, using by default ~/.cache/ssm_search",
    )
    p.add_argument("-p", "--parameter", required=False, help="Parameter name")
    p.add_argument("-l", "--list", action="store_true", help="List all parameters")
    p.add_argument("-r", "--reset", action="store_true", help="Reset cache")
    p.add_argument("-s", "--search", nargs="*", help="Search keywords")
    return vars(p.parse_args())


class SsmClient:
    def __init__(self, config: botocore.config.Config):
        self.client = boto3.client("ssm", config=config)

    def list_parameters(self, beginswith: str = ""):
        paginator = self.client.get_paginator("describe_parameters")

        if beginswith:
            pages = paginator.paginate(
                ParameterFilters=[
                    {
                        "Key": "Path",
                        "Option": "Recursive",
                        "Values": [
                            beginswith,
                        ],
                    },
                ],
                PaginationConfig={
                    "PageSize": 50,
                },
            )
        else:
            pages = paginator.paginate(
                PaginationConfig={
                    "PageSize": 50,
                }
            )

        for p in pages:
            yield p

    def get_parameter(self, name: str) -> str:
        return self.client.get_parameter(Name=name, WithDecryption=True)["Parameter"][
            "Value"
        ]


def main():
    args = parseargs()
    ssm = SsmClient(config=BOTO3_CONFIG)

    cache = Cache(args["cache"])

    if args["reset"]:
        cache.clear()

    if "all_parameters" not in cache:
        all_parameters = []
        for page in ssm.list_parameters(beginswith="/"):
            for parameter in page["Parameters"]:
                all_parameters.append(parameter["Name"])
        cache["all_parameters"] = all_parameters

    try:
        # just list all parameters
        if args["list"]:
            for parameter in cache["all_parameters"]:
                print(parameter)

        # filter all matching parameters
        if args["search"]:
            for parameter_name in cache["all_parameters"]:
                if all(f in parameter_name for f in args["search"]):
                    print(parameter_name, ssm.get_parameter(name=parameter_name))

    except KeyboardInterrupt:
        exit(1)

    # get just parameter by full name
    if args["parameter"]:
        parameter_value = ssm.get_parameter(name=args["parameter"])
        print(parameter_value)

    if not any([args["list"], args["search"], args["parameter"]]):
        print("Use --help for help")


if __name__ == "__main__":
    main()
