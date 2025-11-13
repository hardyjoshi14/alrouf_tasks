from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uvicorn
import uuid
from enum import Enum

class Language(str, Enum):
    AR = "ar"
    EN = "en"

class ClientInfo(BaseModel):
    name: str
    contact: str
    lang: Language = Language.EN

class QuoteItem(BaseModel):
    sku: str
    qty: int = Field(gt=0)
    unit_cost: float = Field(gt=0)
    margin_pct: float = Field(ge=0, le=100)

class EmailDraft(BaseModel):
    primary: str
    alternate: str
    requested_language: str

class QuoteRequest(BaseModel):
    client: ClientInfo
    currency: str = "SAR"
    items: List[QuoteItem]
    delivery_terms: str
    notes: Optional[str] = None

class QuoteResponse(BaseModel):
    quote_id: str
    client: ClientInfo
    currency: str
    items: List[Dict[str, Any]]
    subtotal: float
    total_tax: float
    grand_total: float
    delivery_terms: str
    email_draft: EmailDraft
    notes: Optional[str] = None

app = FastAPI(
    title="Alrouf Quotation Service",
    description="Microservice for generating product quotations with multilingual email drafts",
    version="1.0.0"
)

class QuotationEngine:
    def __init__(self):
        self.tax_rate = 0.15  
    
    def calculate_line_total(self, item: QuoteItem) -> Dict[str, Any]:
        unit_price = item.unit_cost * (1 + item.margin_pct / 100)
        line_total = unit_price * item.qty
        return {
            "sku": item.sku,
            "quantity": item.qty,
            "unit_cost": round(item.unit_cost, 2),
            "margin_pct": item.margin_pct,
            "unit_price": round(unit_price, 2),
            "line_total": round(line_total, 2)
        }
    
    def generate_email_draft(self, quote_data: Dict, lang: Language) -> str:
        if lang == Language.EN:
            return self._generate_english_email(quote_data)
        else:
            return self._generate_arabic_email(quote_data)
    
    def _generate_english_email(self, quote_data: Dict) -> str:
        items_text = "\n".join([
            f"- {item['sku']}: {item['quantity']} pcs × {quote_data['currency']} {item['unit_price']:.2f} = {quote_data['currency']} {item['line_total']:.2f}"
            for item in quote_data['items']
        ])
        
        return f"""Dear {quote_data['client_name']},

Thank you for your inquiry. Please find our quotation below:

**Quotation Summary:**
{items_text}

**Subtotal:** {quote_data['currency']} {quote_data['subtotal']:.2f}
**VAT (15%):** {quote_data['currency']} {quote_data['total_tax']:.2f}
**Grand Total:** {quote_data['currency']} {quote_data['grand_total']:.2f}

**Delivery Terms:** {quote_data['delivery_terms']}

{quote_data['notes'] if quote_data.get('notes') else 'Please feel free to contact us for any clarifications.'}

Best regards,
Alrouf Sales Team
"""
    
    def _generate_arabic_email(self, quote_data: Dict) -> str:
        items_text = "\n".join([
            f"- {item['sku']}: {item['quantity']} قطعة × {item['unit_price']:.2f} {quote_data['currency']} = {item['line_total']:.2f} {quote_data['currency']}"
            for item in quote_data['items']
        ])
        
        return f"""السيد/السيدة {quote_data['client_name']}،

شكراً لاستفساركم. يرجى الاطلاع على عرض الأسعار أدناه:

**ملخص العرض:**
{items_text}

**المجموع الفرعي:** {quote_data['subtotal']:.2f} {quote_data['currency']}
**ضريبة القيمة المضافة (15%):** {quote_data['total_tax']:.2f} {quote_data['currency']}
**المجموع الكلي:** {quote_data['grand_total']:.2f} {quote_data['currency']}

**شروط التسليم:** {quote_data['delivery_terms']}

{quote_data['notes'] if quote_data.get('notes') else 'يرجى عدم التردد في الاتصال بنا لأي توضيحات.'}

مع خالص التحيات،
فريق المبيعات - الرؤف
"""

engine = QuotationEngine()

@app.post("/quote", response_model=QuoteResponse)
async def create_quotation(request: QuoteRequest):
    try:
        # Calculate line items
        calculated_items = []
        subtotal = 0
        
        for item in request.items:
            line_data = engine.calculate_line_total(item)
            calculated_items.append(line_data)
            subtotal += line_data["line_total"]
        
        # Calculate taxes and totals
        total_tax = subtotal * engine.tax_rate
        grand_total = subtotal + total_tax
        
        # Prepare quote data
        quote_data = {
            "client_name": request.client.name,
            "currency": request.currency,
            "items": calculated_items,
            "subtotal": round(subtotal, 2),
            "total_tax": round(total_tax, 2),
            "grand_total": round(grand_total, 2),
            "delivery_terms": request.delivery_terms,
            "notes": request.notes
        }
        
        # Generate email drafts - PRIMARY in requested language, ALTERNATE in other language
        primary_language = request.client.lang
        alternate_language = Language.AR if primary_language == Language.EN else Language.EN
        
        email_draft = EmailDraft(
            primary=engine.generate_email_draft(quote_data, primary_language),
            alternate=engine.generate_email_draft(quote_data, alternate_language),
            requested_language=primary_language.value
        )
        
        # Generate quote ID
        quote_id = f"QR{str(uuid.uuid4())[:8].upper()}"
        
        return QuoteResponse(
            quote_id=quote_id,
            client=request.client,
            currency=request.currency,
            items=calculated_items,
            subtotal=quote_data["subtotal"],
            total_tax=quote_data["total_tax"],
            grand_total=quote_data["grand_total"],
            delivery_terms=request.delivery_terms,
            email_draft=email_draft,
            notes=request.notes
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Quotation generation failed: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "quotation-engine"}

@app.get("/")
async def root():
    return {"message": "Alrouf Quotation Service", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)