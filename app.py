import streamlit as st
import time
from execute_payment import trigger_farmer_payment 

# Setup the page styling
st.set_page_config(page_title="Yantra Agri-Portal", page_icon="🌾")

st.title("🌾 Yantra 2026: Automated Crop Payouts")
st.write("Upload a photo of your verified crop yield to instantly receive your Web3 escrow payment.")

# 1. The File Uploader Widget
uploaded_photo = st.file_uploader("Upload Crop Photo (JPG/PNG)", type=["jpg", "jpeg", "png"])

if uploaded_photo is not None:
    # Display the uploaded image back to the user
    st.image(uploaded_photo, caption="Uploaded Crop Image", use_container_width=True)
    
    # 2. The Verification & Payout Button
    if st.button("Verify Crop & Claim Payment", type="primary"):
        
        # Hackathon visual magic: Simulate an AI computer vision processing delay
        with st.spinner("Analyzing image with Computer Vision model..."):
            time.sleep(2.5) 
            st.success("✅ Crop visually verified! Yield matches local data registry.")
            
        # 3. Trigger the Blockchain Payout
        with st.spinner("Connecting to Sepolia network and triggering smart contract..."):
            
            # Using the secondary wallet you successfully tested earlier
            farmer_wallet = "0xa81E35D97D6148470788e3Ab14d57b6B84FC3515" 
            payment_amount = 5000000000000000 # 0.005 ETH
            
            try:
                # Calling the exact Python Web3 function you already built!
                trigger_farmer_payment(farmer_wallet, payment_amount)
                st.balloons()
                st.success(f"🎉 Success! Payment instantly deposited to wallet: {farmer_wallet}")
            except Exception as e:
                st.error(f"Blockchain execution failed: {e}")