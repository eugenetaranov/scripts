#!/usr/bin/env python

import boto3
import pyotp
import os


def generate_temp_credentials(
    access_key: str, secret_key: str, otp_secret: str, mfa_device: str
) -> dict:
    totp = pyotp.TOTP(otp_secret)
    otp_code = totp.now()

    client = boto3.client(
        "sts", aws_access_key_id=access_key, aws_secret_access_key=secret_key
    )

    response = client.get_session_token(
        DurationSeconds=3600,
        SerialNumber=mfa_device,
        TokenCode=otp_code,
    )

    credentials = response["Credentials"]

    return {
        "aws_access_key_id": credentials["AccessKeyId"],
        "aws_secret_access_key": credentials["SecretAccessKey"],
        "aws_session_token": credentials["SessionToken"],
    }


def main():
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_MFA_SECRET = os.getenv("AWS_MFA_SECRET")
    MFA_DEVICE = os.getenv("MFA_DEVICE")

    credentials = generate_temp_credentials(
        access_key=AWS_ACCESS_KEY_ID,
        secret_key=AWS_SECRET_ACCESS_KEY,
        otp_secret=AWS_MFA_SECRET,
        mfa_device=MFA_DEVICE,
    )

    print(f"export AWS_ACCESS_KEY_ID={credentials['aws_access_key_id']}")
    print(f"export AWS_SECRET_ACCESS_KEY={credentials['aws_secret_access_key']}")
    print(f"export AWS_SESSION_TOKEN={credentials['aws_session_token']}")


if __name__ == "__main__":
    main()
