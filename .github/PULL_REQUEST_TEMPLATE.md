<!-- TerraGuard PR template -->

## What changed

<!-- Briefly describe the infrastructure or code change. -->

## Security impact

- [ ] This PR changes Terraform (`examples/terraform/**` or other `*.tf`)
- [ ] I reviewed the TerraGuard security report comment below
- [ ] No new CRITICAL regressions (the gate blocks merge on CRITICAL)

> TerraGuard runs automatically on Terraform changes: scan → regression tests →
> AI triage → auto-fix PR → posture report. See the bot comment for the score delta.
