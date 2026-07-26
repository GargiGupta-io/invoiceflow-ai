# Terraform State Bootstrap

This small stack creates only the backend used to protect the main InvoiceFlow
Terraform state:

- one private, encrypted, versioned S3 bucket;
- one encrypted, on-demand DynamoDB lock table;
- public-access blocking and TLS-only bucket access; and
- destruction protection on both resources.

It intentionally has no remote backend of its own. Terraform cannot store the
state for a bucket inside that same bucket before the bucket exists. Keep the
local bootstrap state private and use it only for the one-time backend setup.

## Plan Without Creating Resources

Copy the example outside source control and replace its account placeholder:

```bash
cd infra/terraform/bootstrap
cp bootstrap.tfvars.example bootstrap.tfvars

terraform init -backend=false -input=false
AWS_PROFILE=invoiceflow-deploy terraform plan \
  -input=false \
  -var-file=bootstrap.tfvars \
  -out=invoiceflow-bootstrap.tfplan
```

Step 20C stops after reviewing this plan. Do not apply it during permission or
cost review.

## Apply Boundary

The backend plan may be applied only in Step 20D after explicit approval. Once
the bucket and lock table exist, initialize the main stack with the output
names:

```bash
cd ..
AWS_PROFILE=invoiceflow-deploy terraform init -reconfigure \
  -backend-config="bucket=REPLACE_STATE_BUCKET" \
  -backend-config="key=invoiceflow/showcase.tfstate" \
  -backend-config="region=ap-south-1" \
  -backend-config="dynamodb_table=REPLACE_LOCK_TABLE" \
  -backend-config="encrypt=true"
```

Do not commit `bootstrap.tfvars`, state files, lock files, or saved plan files.
