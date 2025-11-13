### Installation 
Clone the repo using git clone
cd alrouf-tasks

### Task 1: RFQ Automation
The folder contains the scenario used to develop the automation. The output google sheet, sample auto-reply mail and the sample attachment have also been included. 

NOTE - Due to inavailability of a CRM, the current scenario just fetches the information from Google sheet and uses those fields in the attachment. In the sample, the client is just asked to use the micrsoservice and enter the details.

The scenario was teseted using the following sample email:  
  Hello Alrouf, please quote 120 pcs streetlight model ALR‑SL‑90W. Needed in Dammam within 4 weeks. Attach specs. Regards, Eng. Omar, +96656734, omar@client.com

### Task 2: Quotation Service
Run these commands in the terminal to test the microservice.  

cd quotation-service  
python -m venv venv  
source venv/bin/activate  
pip install -r requirements.txt  

uvicorn main:app --reload  

In another terminal, run the following request:    
  curl -X POST "http://localhost:8000/quote" \
  -H "Content-Type: application/json" \
  -d '{
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
        "margin_pct": 22
      }
    ],
    "delivery_terms": "DAP Dammam, 4 weeks"
  }'

Sample Arabic request:  
 curl -X POST "http://localhost:8000/quote" \
  -H "Content-Type: application/json" \
  -d '{
    "client": {
      "name": "عميل اختبار",
      "contact": "test@client.com",
      "lang": "ar"
    },
    "currency": "SAR",
    "items": [
      {
        "sku": "TEST-001",
        "qty": 5,
        "unit_cost": 200.0,
        "margin_pct": 15.0
      }
    ],
    "delivery_terms": "DAP الرياض، أسبوعين"
  }'

To test the service run:  
 pytest test_quotation.py -v  

### Task 3: RAG Knowledge Base
Run these commands to test the RAG system.  

cd rag-knowledge-base  
python -m venv venv  
source venv/bin/activate    
pip install -r requirements.txt  

Download ollama and then run:  
 ollama pull llama3  
 ollama serve  

Create vector store  
 python main.py --ingest ./sample_docs  

Sample english question:  
 python main_local.py --question "What is the warranty for streetlight poles?" --lang en  

Sample arabic question:  
 python main_local.py --question "ما هي مدة الضمان لأعمدة الإنارة؟" --lang ar  

Interactive mode:  
 python main.py --cli    

Sample questions (to change language use lang en, or lang ar)  
 What are the delivery terms?  
 What are the product specifications?  
 What certifications are required?  
 ما هي شروط التسليم؟  
 ما هي مواصفات المنتج؟  
 ما هي الشهادات المطلوبة؟  

NOTE - For easier use ollama models have been used so that the system can be tested properly without usage of any API keys.  
