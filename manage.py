#!/usr/bin/env python
"""Run the local development host for the reusable CRM app."""

import os
import sys

from django.core.management import execute_from_command_line

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "devsite.settings")
    execute_from_command_line(sys.argv)
