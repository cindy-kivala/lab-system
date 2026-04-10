#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔐 Getting access token...${NC}"
TOKEN=$(curl -s -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@pharmacy.com","password":"admin123"}' | grep -o '"access_token":"[^"]*' | grep -o '[^"]*$')

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Failed to get token. Is the server running?${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Token received${NC}\n"

# Test 1: Get current user
echo -e "${BLUE}📋 Test 1: Get current user${NC}"
curl -s http://localhost:5001/api/auth/me \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 2: Get all products
echo -e "${BLUE}📦 Test 2: Get all products${NC}"
curl -s http://localhost:5001/api/products \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 3: Get dashboard stats
echo -e "${BLUE}Test 3: Get dashboard stats${NC}"
curl -s http://localhost:5001/api/dashboard/stats \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo -e "\n"

# Test 4: Get inventory
echo -e "${BLUE}📦 Test 4: Get inventory${NC}"
curl -s http://localhost:5001/api/inventory \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo -e "\n"

echo -e "${GREEN} All tests completed!${NC}"