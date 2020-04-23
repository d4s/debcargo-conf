#!/usr/bin/python3
# the excuses file can be found here:
# https://release.debian.org/britney/excuses.yaml

import sys
import yaml

print("parsing excuses.yaml...", file=sys.stderr)
with open("excuses.yaml") as fp:
    y = yaml.load(fp)

for e in y["sources"]:
    package = e.get("source")
    if not package.startswith("rust-"):
        # We only care about rust packages
        continue
    policy_info = e.get("policy_info")
    need_upload = False
    temp_reasons = []
    perm_reasons = []
    for policy, value in policy_info.items():
        if policy == "builtonbuildd" and value.get("verdict") == "REJECTED_PERMANENTLY":
            need_upload = True
        elif value.get("verdict") == "REJECTED_TEMPORARILY":
            temp_reasons.append(policy)
        elif value.get("verdict") == "REJECTED_PERMANENTLY":
            perm_reasons.append(policy)

    if need_upload:
        print("%s needs a source-only upload" % package)
        if len(temp_reasons) > 0:
            print("\tother temporary reasons preventing migration: %s" % ",".join(set(temp_reasons)))
        if len(perm_reasons) > 0:
            print("\tother permanent reasons preventing migration: %s" % ",".join(set(perm_reasons)))
