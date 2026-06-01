# 🚀 ShipMate AI — Azure Deployment Guide

This guide walks you through deploying ShipMate AI to Azure as a complete SaaS product.

---

## Prerequisites

- **Azure Subscription** (with active billing)
- **Azure CLI** installed (`az --version`)
- **Git** installed
- **Node.js 18+** (for local frontend build)
- **Python 3.11+** (for local backend build)
- **GitHub Account** with app creation permissions

---

## Step 1: Create Azure Resources

### 1.1 Create Resource Group
```bash
az group create \
  --name shipmate-rg \
  --location eastus
```

### 1.2 Create Storage Account (for reports)
```bash
az storage account create \
  --name shipmatestorage \
  --resource-group shipmate-rg \
  --location eastus \
  --sku Standard_LRS
```

### 1.3 Create Cosmos DB (for metadata)
```bash
az cosmosdb create \
  --name shipmate-cosmos \
  --resource-group shipmate-rg \
  --locations regionName=eastus \
  --default-consistency-level Eventual
```

### 1.4 Create Application Insights (for telemetry)
```bash
az monitor app-insights component create \
  --app shipmate-insights \
  --location eastus \
  --resource-group shipmate-rg
```

### 1.5 Create Key Vault (for secrets)
```bash
az keyvault create \
  --name shipmate-kv \
  --resource-group shipmate-rg \
  --location eastus
```

### 1.6 Create Azure OpenAI (for LLM)
```bash
# First, request access to Azure OpenAI
# Then deploy GPT-4 model
az cognitiveservices account create \
  --name shipmate-openai \
  --resource-group shipmate-rg \
  --kind OpenAI \
  --sku s0 \
  --location eastus
```

---

## Step 2: Configure Azure OpenAI

### 2.1 Get OpenAI Endpoint and Key
```bash
az cognitiveservices account keys list \
  --name shipmate-openai \
  --resource-group shipmate-rg
```

### 2.2 Store in Key Vault
```bash
az keyvault secret set \
  --vault-name shipmate-kv \
  --name AZURE-OPENAI-ENDPOINT \
  --value "https://shipmate-openai.openai.azure.com/"

az keyvault secret set \
  --vault-name shipmate-kv \
  --name AZURE-OPENAI-API-KEY \
  --value "your-api-key-here"
```

---

## Step 3: Deploy Backend to Azure App Service

### 3.1 Create App Service Plan
```bash
az appservice plan create \
  --name shipmate-plan \
  --resource-group shipmate-rg \
  --sku B2 \
  --is-linux
```

### 3.2 Create Web App
```bash
az webapp create \
  --name shipmate-api \
  --resource-group shipmate-rg \
  --plan shipmate-plan \
  --runtime "python|3.11"
```

### 3.3 Configure App Settings
```bash
az webapp config appsettings set \
  --name shipmate-api \
  --resource-group shipmate-rg \
  --settings \
    AZURE_OPENAI_ENDPOINT="https://shipmate-openai.openai.azure.com/" \
    AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4" \
    AZURE_STORAGE_CONNECTION_STRING="your-storage-connection-string" \
    AZURE_COSMOS_CONNECTION_STRING="your-cosmos-connection-string" \
    APPLICATIONINSIGHTS_CONNECTION_STRING="your-insights-connection-string"
```

### 3.4 Deploy Backend Code
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Deploy
az webapp up \
  --name shipmate-api \
  --resource-group shipmate-rg \
  --runtime "PYTHON:3.11"
```

---

## Step 4: Deploy Frontend to Azure Static Web Apps

### 4.1 Build Frontend
```bash
cd frontend
npm install
npm run build
```

### 4.2 Create Static Web App
```bash
az staticwebapp create \
  --name shipmate-frontend \
  --resource-group shipmate-rg \
  --source . \
  --location eastus \
  --branch main \
  --app-location "frontend" \
  --output-location "dist" \
  --token "$GITHUB_TOKEN"
```

### 4.3 Configure API Proxy (optional)
Static Web Apps can proxy API calls to your backend. Create `staticwebapp.config.json`:

```json
{
  "routes": [
    {
      "route": "/api/*",
      "rewrite": "https://shipmate-api.azurewebsites.net/api/*"
    },
    {
      "route": "/*",
      "serve": "/index.html",
      "statusCode": 200
    }
  ]
}
```

---

## Step 5: Setup GitHub App for OAuth

### 5.1 Create GitHub App
1. Go to GitHub Settings → Developer Settings → GitHub Apps
2. Click "New GitHub App"
3. Fill in:
   - **App name**: ShipMate AI
   - **Homepage URL**: `https://shipmate-frontend.azurewebsites.net`
   - **Authorization callback URL**: `https://shipmate-api.azurewebsites.net/api/github/callback`
   - **Webhook URL**: (optional) `https://shipmate-api.azurewebsites.net/github/webhook`
   - **Webhook secret**: Generate a strong secret

### 5.2 Set Permissions
Under "Repository permissions":
- `Contents`: Read-only
- `Metadata`: Read-only
- `Pull requests`: Read-only
- `Issues`: Read-only
- `Actions`: Read-only

### 5.3 Store App Credentials in Key Vault
```bash
az keyvault secret set \
  --vault-name shipmate-kv \
  --name GITHUB-APP-ID \
  --value "your-app-id"

az keyvault secret set \
  --vault-name shipmate-kv \
  --name GITHUB-APP-PRIVATE-KEY \
  --value "$(cat private-key.pem)"

az keyvault secret set \
  --vault-name shipmate-kv \
  --name GITHUB-WEBHOOK-SECRET \
  --value "your-webhook-secret"
```

### 5.4 Update App Service with GitHub Credentials
```bash
az webapp config appsettings set \
  --name shipmate-api \
  --resource-group shipmate-rg \
  --settings \
    GITHUB_APP_ID="your-app-id" \
    GITHUB_APP_PRIVATE_KEY="your-private-key" \
    GITHUB_WEBHOOK_SECRET="your-webhook-secret"
```

---

## Step 6: Setup CI/CD with GitHub Actions

### 6.1 Create `.github/workflows/deploy.yml`
```yaml
name: Deploy ShipMate AI

on:
  push:
    branches: [ main ]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Deploy to Azure App Service
        uses: azure/webapps-deploy@v2
        with:
          app-name: shipmate-api
          package: backend
          publish-profile: ${{ secrets.AZURE_PUBLISH_PROFILE }}

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Build Frontend
        run: |
          cd frontend
          npm install
          npm run build
      
      - name: Deploy to Static Web Apps
        uses: Azure/static-web-apps-deploy@v1
        with:
          azure_static_web_apps_api_token: ${{ secrets.AZURE_STATIC_WEB_APPS_API_TOKEN }}
          action: 'upload'
          app_location: 'frontend/dist'
```

### 6.2 Add Secrets to GitHub Repository
1. Go to GitHub → Settings → Secrets and variables → Actions
2. Add:
   - `AZURE_PUBLISH_PROFILE`: Get from Azure App Service
   - `AZURE_STATIC_WEB_APPS_API_TOKEN`: Get from Azure Static Web Apps

---

## Step 7: Configure Monitoring & Alerts

### 7.1 View Application Insights
```bash
az monitor app-insights show \
  --name shipmate-insights \
  --resource-group shipmate-rg
```

### 7.2 Create Alert for Errors
```bash
az monitor metrics alert create \
  --name shipmate-error-alert \
  --resource-group shipmate-rg \
  --scopes /subscriptions/{subscription-id}/resourceGroups/shipmate-rg/providers/microsoft.insights/components/shipmate-insights \
  --condition "avg Exception count > 10" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action email-action-group
```

---

## Step 8: Verify Deployment

### 8.1 Test API Endpoints
```bash
curl https://shipmate-api.azurewebsites.net/health
# Should return: {"status": "healthy", ...}

curl https://shipmate-api.azurewebsites.net/api/github/repos
# Should return list of mock repositories
```

### 8.2 Access Frontend
Open `https://shipmate-frontend.azurewebsites.net` in browser.

---

## Scaling Considerations

### Production Recommendations
- **App Service Plan**: Use `B2` or higher for production
- **Database**: Azure Cosmos DB with multi-region replication
- **Storage**: Enable Azure CDN for static content
- **API Management**: Use Azure API Management for rate limiting
- **Load Testing**: Run load tests before going live

### Cost Optimization
- Use **Reserved Instances** for App Service
- Enable **Auto-scaling** for variable load
- Use **Azure Hybrid Benefit** if you have licenses
- Monitor with **Azure Cost Management**

---

## Troubleshooting

### Backend Won't Start
```bash
# Check logs
az webapp log tail --name shipmate-api --resource-group shipmate-rg

# SSH into app
az webapp create-remote-connection --name shipmate-api --resource-group shipmate-rg
```

### Frontend Not Loading
- Check Static Web Apps build logs
- Verify CORS settings in backend
- Check browser DevTools for errors

### GitHub OAuth Not Working
- Verify callback URL matches exactly
- Check GitHub App permissions
- Ensure private key is properly formatted

---

## Security Best Practices

✅ **Always do:**
- Store secrets in Azure Key Vault, never in code
- Use managed identities for Azure service authentication
- Enable Azure DDoS Protection
- Use HTTPS/TLS for all connections
- Regular security audits

❌ **Never do:**
- Commit `.env` files to GitHub
- Share API keys or secrets
- Disable CORS for production
- Use default/weak passwords

---

## Next Steps

1. **Monitor**: Set up Application Insights dashboards
2. **Scale**: Configure auto-scaling policies
3. **Backup**: Enable automated backups for databases
4. **Documentation**: Document your deployment
5. **Team Access**: Configure RBAC for team members

---

## Support & Resources

- [Azure Static Web Apps Docs](https://learn.microsoft.com/en-us/azure/static-web-apps/)
- [Azure App Service Docs](https://learn.microsoft.com/en-us/azure/app-service/)
- [Azure OpenAI Docs](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/)
- [GitHub Apps Documentation](https://docs.github.com/en/developers/apps)

---

**Happy deploying! 🚀**
