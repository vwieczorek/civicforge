#!/bin/bash
# Fix pydantic deployment issue for AWS Lambda

echo "🔧 Fixing pydantic deployment issue..."

# Check current pydantic version
echo "Current pydantic version:"
grep "pydantic" requirements-deploy.txt

# Option 1: Update serverless.yml for proper Docker compilation
echo -e "\n📦 Option 1: Updating serverless.yml for Docker compilation..."
cat > serverless.yml.patch << 'EOF'
--- a/serverless.yml
+++ b/serverless.yml
@@ -94,17 +94,19 @@ custom:
   pythonRequirements:
     # Use Docker for Linux compatibility
-    dockerizePip: non-linux
+    dockerizePip: true
+    dockerImage: public.ecr.aws/sam/build-python3.11:latest
     
     # Use deployment requirements file
     fileName: requirements-deploy.txt
     
     # Don't strip binaries
     strip: false
     
     # Include all files
     slim: false
     
     # Package in function (not layer) for debugging
     layer: false
     
     # Use requirements.txt exactly
     useStaticCache: false
     useDownloadCache: false
+    pipCmdExtraArgs:
+      - --platform manylinux2014_x86_64
+      - --only-binary=:all:
     
     # Don't deploy these AWS SDK packages
     noDeploy:
EOF

echo "To apply Option 1:"
echo "1. Review the patch above"
echo "2. Apply it manually to serverless.yml"
echo "3. Run: serverless deploy --stage staging"

echo -e "\n📦 Option 2: Downgrade to pydantic v1 (if Option 1 fails)..."
echo "Run: ./scripts/downgrade_pydantic.sh"

# Create the downgrade script
cat > scripts/downgrade_pydantic.sh << 'EOF'
#!/bin/bash
# Downgrade to pydantic v1 for Lambda compatibility

echo "Backing up current requirements..."
cp requirements-deploy.txt requirements-deploy.txt.bak

echo "Downgrading to pydantic v1..."
sed -i '' 's/pydantic==.*/pydantic==1.10.13/' requirements-deploy.txt
sed -i '' '/pydantic-settings/d' requirements-deploy.txt

echo "Updated requirements-deploy.txt:"
grep pydantic requirements-deploy.txt

echo -e "\n⚠️  You'll need to update imports in your code:"
echo "Change: from pydantic_settings import BaseSettings"
echo "To:     from pydantic import BaseSettings"

echo -e "\nRun these commands to find files to update:"
echo "grep -r 'pydantic_settings' --include='*.py' ."
echo "grep -r 'Field(' --include='*.py' . | grep -v '.venv'"
EOF

chmod +x scripts/downgrade_pydantic.sh

echo -e "\n✅ Fix script created!"
echo "Choose your approach and redeploy to staging"