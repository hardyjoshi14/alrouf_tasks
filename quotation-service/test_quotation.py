import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.append(os.path.dirname(__file__))

from main import app

client = TestClient(app)

def test_quote_creation_english():
    """Test quotation generation in English"""
    request_data = {
        "client": {
            "name": "Gulf Eng.",
            "contact": "omar@client.com",
            "lang": "en"
        },
        "currency": "SAR",
        "items": [
            {
                "sku": "ALR-SL-90W",
                "qty": 120,
                "unit_cost": 240.0,
                "margin_pct": 22.0
            }
        ],
        "delivery_terms": "DAP Dammam, 4 weeks",
        "notes": "Client asked for spec compliance with Tarsheed."
    }
    
    response = client.post("/quote", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["email_draft"]["requested_language"] == "en"
    assert "Dear Gulf Eng." in data["email_draft"]["primary"]
    assert "السيد/السيدة" in data["email_draft"]["alternate"]

def test_quote_creation_arabic():
    """Test quotation generation in Arabic"""
    request_data = {
        "client": {
            "name": "شركة الخليج",
            "contact": "omar@client.com",
            "lang": "ar"
        },
        "currency": "SAR",
        "items": [
            {
                "sku": "ALR-OBL-12V",
                "qty": 40,
                "unit_cost": 95.5,
                "margin_pct": 18.0
            }
        ],
        "delivery_terms": "DAP الدمام، 4 أسابيع",
        "notes": "يجب التوافق مع مواصفات ترشيد"
    }
    
    response = client.post("/quote", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["email_draft"]["requested_language"] == "ar"
    assert "السيد/السيدة" in data["email_draft"]["primary"]
    assert "Dear" in data["email_draft"]["alternate"]

def test_invalid_item_quantity():
    """Test validation for invalid quantity"""
    request_data = {
        "client": {
            "name": "Test Client",
            "contact": "test@client.com",
            "lang": "en"
        },
        "currency": "SAR",
        "items": [
            {
                "sku": "TEST-SKU",
                "qty": 0,
                "unit_cost": 100.0,
                "margin_pct": 20.0
            }
        ],
        "delivery_terms": "Test delivery"
    }
    
    response = client.post("/quote", json=request_data)
    assert response.status_code == 422

def test_health_check():
    """Test health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_multiple_items_calculation():
    """Test quotation with multiple items"""
    request_data = {
        "client": {
            "name": "Test Client",
            "contact": "test@client.com",
            "lang": "en"
        },
        "currency": "SAR",
        "items": [
            {
                "sku": "ALR-SL-90W",
                "qty": 10,
                "unit_cost": 100.0,
                "margin_pct": 20.0
            },
            {
                "sku": "ALR-OBL-12V", 
                "qty": 5,
                "unit_cost": 50.0,
                "margin_pct": 15.0
            }
        ],
        "delivery_terms": "Test delivery"
    }
    
    response = client.post("/quote", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert len(data["items"]) == 2
    assert data["email_draft"]["requested_language"] == "en"

if __name__ == "__main__":
    pytest.main([__file__, "-v"])