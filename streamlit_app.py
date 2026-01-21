#set up the page
#define calculate_valuation as the base code for the valuation
#return all variables from caluculate_valuation(ticker_symbol)
#define manual_valuation as the a function that calcualtes the dcf based on the manual parameters ())
#create teh UI, two buttons, one for manual one for automatic
#ticker_symbol is equal to the input box for ticker symbol

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
from st_flexible_callout_elements import flexible_callout

if 'auto_result' not in st.session_state:
    st.session_state.auto_result = None

if 'manual_done' not in st.session_state:
    st.session_state.manual_done = False



st.markdown("""
<style>
  * {color: #c6c5b9 !important;}
</style>
""", unsafe_allow_html=True)

st.image("https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?q=80&w=1740&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D", width=3200)

st.set_page_config(page_title="Intrinsic Valuation Calculator", layout="wide")

def calculate_automatic_valuation(ticker_symbol):
  try:
      # ============================================================================
      # SETUP - Get all financial data
      # ============================================================================
      ticker = yf.Ticker(ticker_symbol)
      income_stmt = ticker.financials
      shares_outstanding = ticker.info.get("sharesOutstanding")
   
      if not shares_outstanding:
          return None
   
      cash_flow = ticker.cashflow
      fcf_history = cash_flow.loc['Free Cash Flow'] if 'Free Cash Flow' in cash_flow.index else None
   
      if fcf_history is None or len(fcf_history) == 0:
          return None
   
      info = ticker.info
      financials = ticker.financials
      balance_sheet = ticker.balance_sheet
      cashflow = ticker.cashflow
   
      # ============================================================================
      # STEP 1 - GROWTH RATE ANALYSIS (Historical + Analyst Estimates)
      # ============================================================================
   
      # Historical revenue growth (last 3 years)
      total_revenue = income_stmt.loc["Total Revenue"].sort_index()
   
      Rev_Recent = total_revenue.iloc[-1]
      Rev_minus1 = total_revenue.iloc[-2]
      Rev_minus2 = total_revenue.iloc[-3]
      Rev_minus3 = total_revenue.iloc[-4] if len(total_revenue) >= 4 else total_revenue.iloc[0]
   
      Rev_growth_rate01 = (Rev_Recent - Rev_minus1) / Rev_minus1
      Rev_growth_rate12 = (Rev_minus1 - Rev_minus2) / Rev_minus2
      Rev_growth_rate23 = (Rev_minus2 - Rev_minus3) / Rev_minus3
   
      Rev_Simple_Growth = (Rev_growth_rate01 + Rev_growth_rate12 + Rev_growth_rate23) / 3
      Rev_Compounded_average = ((Rev_Recent / Rev_minus3) ** (1/3) - 1)
      Rev_growth_historical = (Rev_Simple_Growth + Rev_Compounded_average) / 2
   
      # Analyst estimates
      try:
          rev_est = ticker.get_revenue_estimate()
          g0 = rev_est.loc["0y", "growth"]
          g1 = rev_est.loc["+1y", "growth"]
       
          def to_float_growth(x):
              if isinstance(x, str):
                  return float(x.strip('%')) / 100
              return float(x)
       
          g0 = to_float_growth(g0)
          g1 = to_float_growth(g1)
          Rev_future_avg_growth = (g0 + g1) / 2
      except:
          Rev_future_avg_growth = Rev_growth_historical
   
      Expected_growth_rate = (Rev_future_avg_growth + Rev_growth_historical) / 2
      g = Expected_growth_rate
   
      # ============================================================================
      # STEP 2 - DISCOUNT RATE (CAPM)
      # ============================================================================
   
      treasury = yf.Ticker("^TNX")
      risk_free_rate = treasury.info['regularMarketPrice'] / 100
   
      market_cap = info.get('marketCap', 0)
   
      if market_cap >= 2_000_000_000_000:  # $2T+ = Mega Cap
          beta = 1.05
      elif market_cap >= 300_000_000_000:  # $300B-$2T = Big Cap
          beta = 1.2
      elif market_cap >= 10_000_000_000:   # $10B-$300B = Mid Cap
          beta = 1.3
      elif market_cap >= 300_000_000:      # $300M-$10B = Small Cap
          beta = 1.35
      else:                                 # <$300M = Micro Cap
          beta = 1.45
   
      equity_risk_premium = 0.035
      market_return = risk_free_rate + equity_risk_premium
   
      r = (risk_free_rate + beta * (market_return - risk_free_rate))
   
      # ============================================================================
      # STEP 3 - PROJECT 10-YEAR CASH FLOWS (WITH TERMINAL GROWTH BLENDING)
      # ============================================================================
   
      FCF_N = fcf_history.iloc[0] * 1.05
      Free_cash_flow_current = FCF_N
   
      # Define terminal growth rate
      terminal_growth_rate = 0.03  # 3% perpetual growth
   
      # Years 1-3: Use analyst estimate growth rate
      # Years 4-10: Gradually blend from average growth rate (g) to terminal growth rate
      growth_rates = []
      for year in range(1, 11):
          if year <= 3:
              # Years 1-3: Analyst estimate growth
              blended_g = Rev_future_avg_growth
          else:
              # Years 4-10: Blend from average growth to terminal growth
              # As year increases from 4 to 10, the weight shifts from g to terminal_growth_rate
              blend_factor = (10 - year) / 7  # Decreases from 6/7 to 0/7 over years 4-10
              blended_g = g * blend_factor + terminal_growth_rate * (1 - blend_factor)
          growth_rates.append(blended_g)
   
      # Calculate 10-year cash flows with cumulative compounding
      CV1 = FCF_N * (1 + growth_rates[0]) ** 1
      CV2 = FCF_N * (1 + growth_rates[0]) * (1 + growth_rates[1]) ** 1
      CV3 = FCF_N * (1 + growth_rates[0]) * (1 + growth_rates[1]) * (1 + growth_rates[2]) ** 1
      CV4 = FCF_N * (1 + growth_rates[0]) * (1 + growth_rates[1]) * (1 + growth_rates[2]) * (1 + growth_rates[3]) ** 1
      CV5 = FCF_N * (1 + growth_rates[0]) * (1 + growth_rates[1]) * (1 + growth_rates[2]) * (1 + growth_rates[3]) * (1 + growth_rates[4]) ** 1
      CV6 = FCF_N * (1 + growth_rates[0]) * (1 + growth_rates[1]) * (1 + growth_rates[2]) * (1 + growth_rates[3]) * (1 + growth_rates[4]) * (1 + growth_rates[5]) ** 1
      CV7 = FCF_N * (1 + growth_rates[0]) * (1 + growth_rates[1]) * (1 + growth_rates[2]) * (1 + growth_rates[3]) * (1 + growth_rates[4]) * (1 + growth_rates[5]) * (1 + growth_rates[6]) ** 1
      CV8 = FCF_N * (1 + growth_rates[0]) * (1 + growth_rates[1]) * (1 + growth_rates[2]) * (1 + growth_rates[3]) * (1 + growth_rates[4]) * (1 + growth_rates[5]) * (1 + growth_rates[6]) * (1 + growth_rates[7]) ** 1
      CV9 = FCF_N * (1 + growth_rates[0]) * (1 + growth_rates[1]) * (1 + growth_rates[2]) * (1 + growth_rates[3]) * (1 + growth_rates[4]) * (1 + growth_rates[5]) * (1 + growth_rates[6]) * (1 + growth_rates[7]) * (1 + growth_rates[8]) ** 1
      CV10 = FCF_N * (1 + growth_rates[0]) * (1 + growth_rates[1]) * (1 + growth_rates[2]) * (1 + growth_rates[3]) * (1 + growth_rates[4]) * (1 + growth_rates[5]) * (1 + growth_rates[6]) * (1 + growth_rates[7]) * (1 + growth_rates[8]) * (1 + growth_rates[9]) ** 1
   
      # ============================================================================
      # STEP 4 - TERMINAL VALUE (Gordon + Multiple Hybrid)
      # ============================================================================
   
      EBITDA_at_year_N = info.get('ebitda', 0)
      perpetual_g = 0.03
      exit_multiple = 10.0
      number_of_years_TV = 10
   
      TV_Gordon_extra_multiple = 1
      Tv_multiple_extra_multiple = 1
   
      # Gordon Growth
      if r > perpetual_g:
          TV_gordon = CV10 * (1 + perpetual_g) / (r - perpetual_g)
          PV_TV_gordon = TV_gordon / ((1 + r) ** number_of_years_TV) * TV_Gordon_extra_multiple
      else:
          PV_TV_gordon = 0
   
      # Multiple method
      if EBITDA_at_year_N and EBITDA_at_year_N > 0:
          TV_multiple = EBITDA_at_year_N * exit_multiple
          PV_TV_multiple = TV_multiple / ((1 + r) ** number_of_years_TV) * Tv_multiple_extra_multiple
      else:
          PV_TV_multiple = 0
   
      market_cap = info.get('marketCap', 0)
      market_cap_buffer = market_cap / 10 if market_cap > 0 else 0
   
      PV_TV = (PV_TV_multiple + PV_TV_gordon + market_cap_buffer) / 2 if (PV_TV_multiple + PV_TV_gordon) > 0 else 0
   
      # ============================================================================
      # STEP 5 - DCF VALUATION
      # ============================================================================
   
      DCF = (CV1 / (1 + r) + CV2 / ((1 + r) ** 2) + CV3 / ((1 + r) ** 3) +
             CV4 / ((1 + r) ** 4) + CV5 / ((1 + r) ** 5) + CV6 / ((1 + r) ** 6) +
             CV7 / ((1 + r) ** 7) + CV8 / ((1 + r) ** 8) + CV9 / ((1 + r) ** 9) +
             CV10 / ((1 + r) ** 10) + PV_TV)
   
      DCF_Per_Share = DCF / shares_outstanding
      DCF_intrinsic_value = DCF
   
      # ============================================================================
      # STEP 6 - DDM ELIGIBILITY CHECK
      # ============================================================================
   
      def check_ddm_conditions(ticker_obj):
          try:
              info = ticker_obj.info
              divs = ticker_obj.dividends
           
              # Sector check
              sector = info.get('sector', '').lower()
              DDM_mature_sectors = ['utilities', 'real estate', 'consumer staples',
                                    'communication services', 'financial services', 'healthcare', 'energy']
              DDM_is_mature_sector = any(s in sector for s in DDM_mature_sectors)
           
              # Dividend exists
              DDM_dividend_rate = info.get('dividendRate', 0)
              DDM_has_dividend = DDM_dividend_rate > 0
           
              # History (5+ years)
              DDM_history_length = len(divs)
              DDM_has_history = DDM_history_length >= 20
           
              # Yield check
              DDM_price = info.get('currentPrice', info.get('regularMarketPrice', 1))
              DDM_yield = (DDM_dividend_rate / DDM_price) if DDM_price > 0 else 0
              DDM_high_yield = DDM_yield >= 0.025
           
              # Payout ratio
              DDM_payout_ratio = info.get('payoutRatio', 0)
              if DDM_payout_ratio is None:
                  DDM_payout_ratio = 0
              DDM_max_payout = 3.0 if 'real estate' in sector else 1.0
              DDM_good_payout = 0.30 <= DDM_payout_ratio <= DDM_max_payout
           
              # EPS
              DDM_has_earnings = info.get('trailingEps', 0) > 0
           
              # All conditions
              DDM_all_conditions_met = (DDM_has_dividend and DDM_has_history and DDM_high_yield and
                                        DDM_good_payout and DDM_has_earnings and DDM_is_mature_sector)
           
              return DDM_all_conditions_met, {
                  'sector': sector,
                  'dividend': DDM_dividend_rate,
                  'history': DDM_history_length,
                  'yield': DDM_yield,
                  'payout': DDM_payout_ratio
              }
          except:
              return False, {}
   
      DDM_is_eligible, DDM_data = check_ddm_conditions(ticker)
   
      # ============================================================================
      # STEP 7 - DDM VALUATION (if eligible)
      # ============================================================================
   
      DDM_intrinsic_value = None
      DDM_is_used = False
   
      if DDM_is_eligible:
          try:
              DDM_required_return = r
              DDM_growth_rate = g
           
              DDM_current_dividend = info.get('dividendRate', 0)
           
              if DDM_current_dividend > 0 and DDM_required_return > DDM_growth_rate:
                  DDM_next_dividend = DDM_current_dividend * (1 + DDM_growth_rate)
                  DDM_intrinsic_value = DDM_next_dividend / (DDM_required_return - DDM_growth_rate)
                  DDM_is_used = True
          except:
              DDM_is_used = False
   
      # ============================================================================
      # STEP 8 - COMBINE DDM + DCF
      # ============================================================================
   
      if DDM_is_used:
          intrinsic_value = (DDM_intrinsic_value + DCF_Per_Share) / 2
      else:
          intrinsic_value = DCF_Per_Share
   
      # ============================================================================
      # STEP 9 - ADJUSTMENT MULTIPLIERS
      # ============================================================================
   
      # EBITDA Margin
      ebitda_margin = (financials.loc['EBITDA'].iloc[0] / financials.loc['Total Revenue'].iloc[0]) * 100
      if ebitda_margin > 30:
          mult_ebitda = 1.2
      elif ebitda_margin > 20:
          mult_ebitda = 1.1
      elif ebitda_margin > 10:
          mult_ebitda = 1.05
      elif ebitda_margin > 5:
          mult_ebitda = 1.00
      else:
          mult_ebitda = 0.95
   
      # D/E Ratio
      de_ratio = balance_sheet.loc['Total Debt'].iloc[0] / balance_sheet.loc['Stockholders Equity'].iloc[0]
      if de_ratio < 0.5:
          mult_de = 1.1
      elif de_ratio < 1.0:
          mult_de = 1.05
      elif de_ratio < 1.5:
          mult_de = 1.00
      elif de_ratio < 2.0:
          mult_de = 0.96
      else:
          mult_de = 0.92
   
      # CapEx Ratio
      ocf = cashflow.loc['Operating Cash Flow'].iloc[0]
      capex = abs(cashflow.loc['Capital Expenditure'].iloc[0])
      capex_ratio = ocf / capex if capex > 0 else 0
      if capex_ratio > 2.5:
          mult_capex = 1.1
      elif capex_ratio > 2.0:
          mult_capex = 1.05
      elif capex_ratio > 1.5:
          mult_capex = 1.00
      elif capex_ratio > 1.0:
          mult_capex = 0.97
      else:
          mult_capex = 0.93
   
      # ROE
      roe = (financials.loc['Net Income'].iloc[0] / balance_sheet.loc['Stockholders Equity'].iloc[0]) * 100
      if roe > 20:
          mult_roe = 1.1
      elif roe > 15:
          mult_roe = 1.05
      elif roe > 10:
          mult_roe = 1.00
      elif roe > 5:
          mult_roe = 0.96
      else:
          mult_roe = 0.92
   
      # Current Ratio
      current_ratio = balance_sheet.loc['Current Assets'].iloc[0] / balance_sheet.loc['Current Liabilities'].iloc[0]
      if current_ratio > 2.0:
          mult_current = 1.15
      elif current_ratio > 1.5:
          mult_current = 1.05
      elif current_ratio > 1.2:
          mult_current = 1.00
      elif current_ratio > 1.0:
          mult_current = 0.96
      else:
          mult_current = 0.90
   
      # ============================================================================
      # STEP 10 - COMPOSITE MULTIPLIER & FINAL VALUATION
      # ============================================================================
   
      composite = (mult_ebitda + mult_de + mult_capex + mult_roe + mult_current ) / 5
      adjusted_value = intrinsic_value * composite
   
      # Current price for comparison
      current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
      upside = ((adjusted_value - current_price) / current_price * 100) if current_price > 0 else 0
   
      # ============================================================================
      # RETURN ALL RESULTS
      # ============================================================================
   
      return {
          'ticker': ticker_symbol,
          'current_price': current_price,
       
          # Growth metrics
          'rev_growth_historical': Rev_growth_historical * 100,
          'rev_growth_analyst': Rev_future_avg_growth * 100,
          'expected_growth_rate': g * 100,
       
          # Discount rate
          'risk_free_rate': risk_free_rate * 100,
          'beta': beta,
          'discount_rate': r * 100,
       
          # Cash flows (10 years)
          'fcf_current': FCF_N,
          'fcf_y1': CV1,
          'fcf_y2': CV2,
          'fcf_y3': CV3,
          'fcf_y4': CV4,
          'fcf_y5': CV5,
          'fcf_y6': CV6,
          'fcf_y7': CV7,
          'fcf_y8': CV8,
          'fcf_y9': CV9,
          'fcf_y10': CV10,
       
          # Terminal value components
          'pv_tv_gordon': PV_TV_gordon,
          'pv_tv_multiple': PV_TV_multiple,
          'pv_tv_final': PV_TV,
       
          # Valuations
          'dcf_total': DCF,
          'dcf_per_share': DCF_Per_Share,
          'ddm_per_share': DDM_intrinsic_value,
          'ddm_is_used': DDM_is_used,
          'base_value': intrinsic_value,
       
          # Adjustment factors
          'ebitda_margin': ebitda_margin,
          'mult_ebitda': mult_ebitda,
          'de_ratio': de_ratio,
          'mult_de': mult_de,
          'capex_ratio': capex_ratio,
          'mult_capex': mult_capex,
          'roe': roe,
          'mult_roe': mult_roe,
          'current_ratio': current_ratio,
          'mult_current': mult_current,
          'composite_multiplier': composite,
       
          # Final value
          'adjusted_value': adjusted_value,
          'upside': upside,
          'market_cap': market_cap
      }
  except Exception as e:
      return None
def calculate_manual_valuation(ticker_symbol, short_term_growth, perpetual_growth, beta_multiplier, risk_free_rate, cf1_growth, cf2_growth, cf3_growth, cf4_growth, cf5_growth, cf6_growth, cf7_growth, cf8_growth, cf9_growth, cf10_growth, multiplier):
    try:
        stock = yf.Ticker(ticker_symbol)
        shares_outstanding = stock.info.get("sha    resOutstanding")
        ar = calculate_automatic_valuation(ticker_input)
        info = stock.info 
        # Manual inputs converted to decimal
        g = short_term_growth / 100
        pg = perpetual_growth / 100
        bm = beta_multiplier
        rsg = risk_free_rate / 100
        c1g = cf1_growth/100
        c2g = cf2_growth/100
        c3g = cf3_growth/100
        c4g = cf4_growth/100
        c5g = cf5_growth/100
        c6g = cf6_growth/100
        c7g = cf7_growth/100
        c8g = cf8_growth/100
        c9g = cf9_growth/100
        c10g = cf10_growth/100
        m = multiplier
        
        # Calculate cash flows
        M_FCF_N = ar['fcf_current']
        m_cv1 = M_FCF_N * (1 + c1g)
        m_cv2 = M_FCF_N * (1 + c1g) * (1 + c2g)
        m_cv3 = M_FCF_N * (1 + c1g) * (1 + c2g) * (1 + c3g)
        m_cv4 = M_FCF_N * (1 + c1g) * (1 + c2g) * (1 + c3g) * (1 + c4g)
        m_cv5 = M_FCF_N * (1 + c1g) * (1 + c2g) * (1 + c3g) * (1 + c4g) * (1 + c5g)
        m_cv6 = M_FCF_N * (1 + c1g) * (1 + c2g) * (1 + c3g) * (1 + c4g) * (1 + c5g) * (1 + c6g)
        m_cv7 = M_FCF_N * (1 + c1g) * (1 + c2g) * (1 + c3g) * (1 + c4g) * (1 + c5g) * (1 + c6g) * (1 + c7g)
        m_cv8 = M_FCF_N * (1 + c1g) * (1 + c2g) * (1 + c3g) * (1 + c4g) * (1 + c5g) * (1 + c6g) * (1 + c7g) * (1 + c8g)
        m_cv9 = M_FCF_N * (1 + c1g) * (1 + c2g) * (1 + c3g) * (1 + c4g) * (1 + c5g) * (1 + c6g) * (1 + c7g) * (1 + c8g) * (1 + c9g)
        m_cv10 = M_FCF_N * (1 + c1g) * (1 + c2g) * (1 + c3g) * (1 + c4g) * (1 + c5g) * (1 + c6g) * (1 + c7g) * (1 + c8g) * (1 + c9g) * (1 + c10g)


        #calculate discount rate
        equity_risk_premium = 0.035
        market_return = rsg + equity_risk_premium
        r = (rsg + bm * (market_return - rsg))


        #calculate terminal value
        EBITDA_at_year_N = info.get('ebitda', 0)
        exit_multiple = 10.0
        number_of_years_TV = 10
        TV_Gordon_extra_multiple = 1
        Tv_multiple_extra_multiple = 1
   
        # Gordon Growth
        if r > pg:
            TV_gordon = m_cv10 * (1 + pg) / (r - pg)
            PV_TV_gordon = TV_gordon / ((1 + r) ** number_of_years_TV) * TV_Gordon_extra_multiple
        else:
            PV_TV_gordon = 0
   
        # Multiple method
        if EBITDA_at_year_N and EBITDA_at_year_N > 0:
            TV_multiple = EBITDA_at_year_N * exit_multiple
            PV_TV_multiple = TV_multiple / ((1 + r) ** number_of_years_TV) * Tv_multiple_extra_multiple
        else:
            PV_TV_multiple = 0
   
        market_cap = info.get('marketCap', 0)
        market_cap_buffer = market_cap / 10 if market_cap > 0 else 0
   
        PV_TV = (PV_TV_multiple + PV_TV_gordon + market_cap_buffer) / 2 if (PV_TV_multiple + PV_TV_gordon) > 0 else 0

        #calculate DCF
        manual_dcf = (m_cv1 / (1 + r) + m_cv2 / ((1 + r) ** 2) + m_cv3 / ((1 + r) ** 3) +
             m_cv4 / ((1 + r) ** 4) + m_cv5 / ((1 + r) ** 5) + m_cv6 / ((1 + r) ** 6) +
             m_cv7 / ((1 + r) ** 7) + m_cv8 / ((1 + r) ** 8) + m_cv9 / ((1 + r) ** 9) +
             m_cv10 / ((1 + r) ** 10) + PV_TV)
        m_dcf_pershare = (manual_dcf*m)/shares_outstanding
        return {
            'm_dcf': m_dcf_pershare,
            'cfg1': c1g,
            'cfg2': c2g,
            'cfg3': c3g,
            'cfg4': c4g,
            'cfg5': c5g,
            'cfg6': c6g,
            'cfg7': c7g,
            'cfg8': c8g,
            'cfg9': c9g,
            'cfg10': c10g,
            'multiplier': m,
            'risk free rate': rsg,
            'beta': bm,
            'M_FCF_N': M_FCF_N,
            'm_cv1' : m_cv1,
            'm_cv2': m_cv2,
            'm_cv3':m_cv3,
            'm_cv4': m_cv4,
            'm_cv5' : m_cv5,
            'm_cv6' :m_cv6,
            'm_cv7' : m_cv7,
            'm_cv8' :m_cv8,
            'm_cv9' :m_cv9,
            'm_cv10':m_cv10,
            'discount_rate' :r,
            'Gordon_TV':PV_TV_gordon,
            'Multiple_TV':PV_TV_multiple,
            'TV': PV_TV,
        }
    except Exception as e:
        st.error(f"Error in manual calculation: {str(e)}")
        return None

st.title("Automating intrinsic valuation for the average person")

ticker_input = st.text_input("Enter Ticker Symbol (e.g., NVDA, MSFT, AAPL)").upper()

st.markdown("""
<div style='
  background-color: #000000;
  color: #FFFFFF;
  padding: 20px;
  border-radius: 10px;
  border-left: 5px solid #FFFFFF;
  margin-bottom: 20px;
  font-size: 16px;
  line-height: 1.7;
'>
What is this tool and what is it used for?

This is a calculator that automatically calculates the intrinsic value of a stock based on the user's input, helping the user with value investment.

But what even is intrinsic valuation?

Intrinsic valuation is the calculation of the 'fair' value of a company based on the fundamentals of the company (base information about the company available on financial statements.)
It is the cornerstone of value investing, which is the method of investing that focuses on cheap-undervalued stocks to buy, betting that the market will eventually realize the true value.
It is used by some of the most famous and successful investors of all time, including: Benjamin Graham, Warren Buffett, and Charlie Munger.

DCF vs DDM Valuation

Discounted cash flow (DCF) valuation projects the future cash flows an asset (company, project, property, etc.) is expected to produce and then converts those
future amounts into a single present value using a discount rate. On the other hand, the second most commonly used valuation model is DDM valuation. The Dividend Discount Model (DDM)
says the intrinsic value of a stock equals the present value of all future dividends the shareholder will receive. The two methods of valuation contrast, and the most commonly used
method is the DCF valuation model. The reason why this is the case is because DDM valuation is mostly only used for large blue chip companies that have a large & consistent dividend
, with minimal growth; it relies on dividend throughout the years, and does not account for growth at all. This means that DDM is only suitable for certain companies.
For most firms that reinvest their capital and do not pay dividends, DCF models are more commonly used.
       
This model combines DCF (cash flow projections), DDM (dividends when applicable), and 6 financial metric based multipliers to create a weighted-final-intrinsic value.
      
This model is not perfect, ALWAYS do your research before investing. DO NOT rely on this model for investments
</div>
""", unsafe_allow_html=True)

if st.button("BEGINNERS: Calculate automatic intrinsic valuation (less accurate but faster) Detailed explanations and guides", use_container_width=True):
  if ticker_input:
      with st.spinner(f"Calculating intrinsic valuation for {ticker_input}..."):
          automatic_result = calculate_automatic_valuation(ticker_input)
      if automatic_result is None:
          st.error(f"Could not fetch data for {ticker_input}, please try again!")
      else:
          r = automatic_result
          # ================================================================
          # VALUATION SUMMARY
          # ================================================================
          st.divider()
          st.subheader('Valuation Summary: ')
          st.caption('**This model is not perfect, ALWAYS do your research before investing. DO NOT rely on this model for investments**')
       
          col1, col2, col3, col4, col5 = st.columns(5)
          with col1:
              st.metric("Current Price", f"${r['current_price']:.2f}")
          with col2:
              st.metric("Final Intrinsic Value", f"${r['adjusted_value']:.2f}")
          with col3:
              st.metric("DCF valuation", f"${r['dcf_per_share']:.2f}")
          with col4:
              st.metric("DDM valuation", f"{r['ddm_per_share']}")
          with col5:
              st.metric("Composite adjustment multiplier", f"{r['composite_multiplier']:.2f}x")
       
          col1, col2 = st.columns(2)                
          with col1:
              if r['upside'] > 0:
                  st.success(f"✅ UNDERVALUED by {r['upside']:.1f}%")
              elif r['upside'] < 0:
                  st.error(f"⚠️ OVERVALUED by {abs(r['upside']):.1f}%, the ")
              else:
                  st.info("➖ FAIRLY VALUED")
       
          with col2:
              if r['ddm_is_used']:
                  st.info(f"✓ DDM Applied (${r['ddm_per_share']:.2f}/share)")
              else:
                  st.info("✗ DDM Not Applicable")
          flexible_callout("""
              What is intrinsic valuation
              What does this value actually mean and how can you interpret it
              How can it be interpreted
              """,
              background_color="#000000",    # Dark navy blue
              font_color="#FFFFFF",          # Light yellow/gold
              font_size=16,
              alignment="left",
              line_height=1.7,
              padding=20,
          )
          # ================================================================
          # GROWTH ANALYSIS
          # ================================================================
          st.divider()
          st.subheader("Growth Rate Analysis")
       
          col1, col2, col3 = st.columns(3)
          with col1:
              st.metric("Historical Revenue Growth (3y avg)", f"{r['rev_growth_historical']:.2f}%")
          with col2:
              st.metric("Analyst Consensus Growth (0y+1y avg)", f"{r['rev_growth_analyst']:.2f}%")
          with col3:
              st.metric("Expected Growth Rate (combined)", f"{r['expected_growth_rate']:.2f}%")
          flexible_callout("""
              Why is this important?
              What is it?
              """,
              background_color="#000000",    # Dark navy blue
              font_color="#FFFFFF",          # Light yellow/gold
              font_size=16,
              alignment="left",
              line_height=1.7,
              padding=20,
          )
       
          # ================================================================
          # DISCOUNT RATE (CAPM)
          # ================================================================
          st.divider()
          st.subheader("Discount Rate (CAPM)")
       
          col1, col2, col3 = st.columns(3)
          with col1:
              st.metric("Risk-Free Rate (10Y Treasury)", f"{r['risk_free_rate']:.2f}%")
          with col2:
              st.metric("Market Cap Based Beta", f"{r['beta']:.2f}")
          with col3:
              st.metric("Discount Rate (r)", f"{r['discount_rate']:.2f}%")
          flexible_callout("""
              What is it and what does it mean?
              Why is it important
              """,
              background_color="#000000",    # Dark navy blue
              font_color="#FFFFFF",          # Light yellow/gold
              font_size=16,
              alignment="left",
              line_height=1.7,
              padding=20,
          )
          st.caption("Formula: r = (Rf + β(Rm - Rf))")
       
          # ================================================================
          # 5-YEAR CASH FLOW PROJECTIONS
          # ================================================================
          st.divider()
          st.subheader("5-Year FCF Projections")
       
          cf_table = pd.DataFrame({
            'Year': ['Current (Y0)', 'Year 1', 'Year 2', 'Year 3', 'Year 4', 'Year 5', 'Year 6', 'Year 7', 'Year 8', 'Year 9', 'Year 10'],
            'Projected FCF': [
            f"${r['fcf_current']:,.0f}",
            f"${r['fcf_y1']:,.0f}",
            f"${r['fcf_y2']:,.0f}",
            f"${r['fcf_y3']:,.0f}",
            f"${r['fcf_y4']:,.0f}",
            f"${r['fcf_y5']:,.0f}",
            f"${r['fcf_y6']:,.0f}",
            f"${r['fcf_y7']:,.0f}",
            f"${r['fcf_y8']:,.0f}",
            f"${r['fcf_y9']:,.0f}",
            f"${r['fcf_y10']:,.0f}"
          ]
          })
          st.table(cf_table)
          flexible_callout("""
              This is ...
              This is used for...
              """,
              background_color="#000000",    # Dark navy blue
              font_color="#FFFFFF",          # Light yellow/gold
              font_size=16,
              alignment="left",
              line_height=1.7,
              padding=20,
          )
          # ================================================================
          # TERMINAL VALUE
          # ================================================================
          st.divider()
          st.subheader("Terminal Value Calculation")
       
          col1, col2, col3 = st.columns(3)
          with col1:
              st.metric("Gordon Growth TV (PV)", f"${r['pv_tv_gordon']:,.0f}")
          with col2:
              st.metric("Multiple-Based TV (PV)", f"${r['pv_tv_multiple']:,.0f}")
          with col3:
              st.metric("Hybrid Average TV (PV)", f"${r['pv_tv_final']:,.0f}")
          flexible_callout("""
              What is the terminal value in intrinsic valuation
              What does it mean?
                           explain the assumptions used
                           What multiples were used whata the perpetual growth rate
              """,
              background_color="#000000",    # Dark navy blue
              font_color="#FFFFFF",          # Light yellow/gold
              font_size=16,
              alignment="left",
              line_height=1.7,
              padding=20,
          )
          st.caption("Terminal value combines Gordon Growth Model, EBITDA multiple exit, and market cap buffer")
       
          # ================================================================
          # DCF DETAILS
          # ================================================================
          st.divider()
          st.subheader("Discounted-Cash-Flow Valuation Details")
       
          col1, col2, col3= st.columns(3)
          with col1:
              st.metric("Total Enterprise Value", f"${r['dcf_total']:,.0f}")
          with col2:
              st.metric("DCF per Share", f"${r['dcf_per_share']:.2f}")
          with col3:
              st.metric("Market Cap", f"${r['market_cap']:,.0f}")
          # ================================================================
          # ADJUSTMENT MULTIPLIERS
          # ================================================================
          st.divider()
          st.subheader("Financial metrics Adjustment Multipliers")
       
          col1, col2 = st.columns(2)
       
          with col1:
              st.write("**Profitability & Efficiency:**")
              st.write(f"• EBITDA Margin: {r['ebitda_margin']:.2f}% → {r['mult_ebitda']:.2f}x")
              st.write(f"• ROE: {r['roe']:.2f}% → {r['mult_roe']:.2f}x")
       
          with col2:
              st.write("**Leverage & Liquidity:**")
              st.write(f"• D/E Ratio: {r['de_ratio']:.2f} → {r['mult_de']:.2f}x")
              st.write(f"• Current Ratio: {r['current_ratio']:.2f} → {r['mult_current']:.2f}x")
       
          col1, col2 = st.columns(2)
       
          with col1:
              st.write("**Capital Allocation:**")
              st.write(f"• CapEx Ratio: {r['capex_ratio']:.2f} → {r['mult_capex']:.2f}x")
       
          flexible_callout("""
              explain why these multipliers exist and what they do, and how they make my product unique
              Profitability & Efficiency: Ebitda margin and ROE. These are...
              Capital Allocation: Capex. This is...
              Leverage & Liquidity: D/E ratio and current ratio. These are...
              """,
              background_color="#000000",    # Dark navy blue
              font_color="#FFFFFF",          # Light yellow/gold
              font_size=16,
              alignment="left",
              line_height=1.7,
              padding=20,
          )
          st.divider()
if st.button("ADVANCED: Calculate manual intrinsic valuation (slower, accuracy based on user's inputs) The valuation is based on user's skill and knowledge", use_container_width=True):
    if ticker_input:
        with st.spinner(f"Calculating automatic valuation for {ticker_input} as a guideline..."):
            st.session_state.auto_result = calculate_automatic_valuation(ticker_input)
    else:
        st.error("Please enter a ticker symbol!")

# ADVANCED SECTION DISPLAYS HERE - OUTSIDE BUTTON
if st.session_state.auto_result is not None:
    ar = st.session_state.auto_result
    
    st.divider()
    st.subheader("Manual Intrinsic Valuation")
    
    with st.expander("Manual Parameter Adjustment", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            short_term_growth = st.slider(
                "Short Term Growth Rate (%)", 
                min_value=0.0001, 
                max_value=199.9999,
                value=ar['expected_growth_rate'],
                key="manual_short_term_growth"
            )
        
        with col2:
            perpetual_growth = st.slider(
                "Perpetual Growth Rate (%)", 
                min_value=0.0001, 
                max_value=10.0,
                value=3.0,
                key="manual_perpetual_growth"
            )
        
        with col3:
            beta_multiplier = st.slider(
                "Beta/Volatility Multiplier", 
                min_value=0.5, 
                max_value=2.5,
                value=ar['beta'],
                step=0.05,
                key="manual_beta"
            )
        
        with col4:
            risk_free_rate = st.slider(
                "Risk Free Rate (%)", 
                min_value=0.0001, 
                max_value=15.0,
                value=ar['risk_free_rate'],
                key="manual_risk_free"
            )
        
        st.write("**Cash Flow Growth Rates for Each Year (%)**")
        
        cf_col1, cf_col2, cf_col3, cf_col4, cf_col5 = st.columns(5)
        
        with cf_col1:
            cf1_growth = st.slider(
                "CF Year 1 Growth (%)", 
                min_value=0.0001, 
                max_value=100.001,
                value=ar['rev_growth_analyst'],
                key="manual_cf1_growth"
            )
            cf2_growth = st.slider(
                "CF Year 2 Growth (%)", 
                min_value=0.0001, 
                max_value=100.001,
                value=ar['rev_growth_analyst'],
                key="manual_cf2_growth"
            )
        
        with cf_col2:
            cf3_growth = st.slider(
                "CF Year 3 Growth (%)", 
                min_value=0.0001, 
                max_value=100.001,
                value=ar['rev_growth_analyst'],
                key="manual_cf3_growth"
            )
            cf4_growth = st.slider(
                "CF Year 4 Growth (%)", 
                min_value=0.0001, 
                max_value=100.001,
                value=ar['expected_growth_rate'],
                key="manual_cf4_growth"
            )
        
        with cf_col3:
            cf5_growth = st.slider(
                "CF Year 5 Growth (%)", 
                min_value=0.0001, 
                max_value=100.001,
                value=ar['expected_growth_rate'],
                key="manual_cf5_growth"
            )
            cf6_growth = st.slider(
                "CF Year 6 Growth (%)", 
                min_value=0.0001, 
                max_value=100.001,
                value=ar['expected_growth_rate'],
                key="manual_cf6_growth"
            )
        
        with cf_col4:
            cf7_growth = st.slider(
                "CF Year 7 Growth (%)", 
                min_value=0.0001, 
                max_value=100.001,
                value=ar['expected_growth_rate'],
                key="manual_cf7_growth"
            )
            cf8_growth = st.slider(
                "CF Year 8 Growth (%)", 
                min_value=0.0001, 
                max_value=100.001,
                value=ar['expected_growth_rate'],
                key="manual_cf8_growth"
            )
        
        with cf_col5:
            cf9_growth = st.slider(
                "CF Year 9 Growth (%)", 
                min_value=0.0001, 
                max_value=100.001,
                value=ar['expected_growth_rate'],
                key="manual_cf9_growth"
            )
            cf10_growth = st.slider(
                "CF Year 10 Growth (%)", 
                min_value=0.0001, 
                max_value=100.001,
                value=ar['expected_growth_rate'],
                key="manual_cf10_growth"
            )
        
        st.write("**Adjustment Factor**")
        
        multiplier = st.number_input(
            "Adjustment Multiplier", 
            min_value=0.5, 
            max_value=2.0, 
            value=ar['composite_multiplier'],
            step=0.01,
            key="manual_multiplier"
        )
        
        if st.button("CALCULATE MANUAL VALUATION", use_container_width=True, key="calc_manual"):
            st.session_state.manual_done = True
    
    # MANUAL RESULTS DISPLAY - OUTSIDE THE BUTTON
    if st.session_state.manual_done:
        st.divider()
        st.subheader(f'Manual Intrinsic Valuation Results for {ticker_input}')
        
        mr = calculate_manual_valuation(
            ticker_input, short_term_growth, perpetual_growth, beta_multiplier, risk_free_rate, cf1_growth, cf2_growth, cf3_growth, cf4_growth, cf5_growth, cf6_growth, cf7_growth, cf8_growth, cf9_growth, cf10_growth, multiplier
        )
        
        if mr is not None:
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            with col1:
                st.metric("Current Price", f"${ar['current_price']:.2f}")
            with col2:
                st.metric("Manually calculated Valuation", f"${mr['m_dcf']:.2f}")
            with col3:
                st.metric("Manually calculated Discount Rate", f"${mr['m_dcf']:.2f}")
            with col4:
                st.metric("Manually calculated terminal value (Gordon)", f"${mr['m_dcf']:.2f}")
            with col5:
                st.metric("Manually calcualted terminal value (multiples)", f"${mr['m_dcf']:.2f}")
            with col6:
                st.metric("Manually calculated terminal value", f"${mr['m_dcf']:.2f}")
            manual_cf_table = pd.DataFrame({
            'Year': ['Current (Y0)', 'Year 1', 'Year 2', 'Year 3', 'Year 4', 'Year 5', 'Year 6', 'Year 7', 'Year 8', 'Year 9', 'Year 10'],
            'Growth Rate (%)': [
                '-', 
                f"{mr['cfg1']*100:.1f}%",
                f"{mr['cfg2']*100:.1f}%",
                f"{mr['cfg3']*100:.1f}%",
                f"{mr['cfg4']*100:.1f}%",
                f"{mr['cfg5']*100:.1f}%",
                f"{mr['cfg6']*100:.1f}%",
                f"{mr['cfg7']*100:.1f}%",
                f"{mr['cfg8']*100:.1f}%",
                f"{mr['cfg9']*100:.1f}%",
                f"{mr['cfg10']*100:.1f}%"
            ],
            'Projected FCF': [
                f"${mr['M_FCF_N']:,.0f}",
                f"${mr['m_cv1']:,.0f}",
                f"${mr['m_cv2']:,.0f}",
                f"${mr['m_cv3']:,.0f}",
                f"${mr['m_cv4']:,.0f}",
                f"${mr['m_cv5']:,.0f}",
                f"${mr['m_cv6']:,.0f}",
                f"${mr['m_cv7']:,.0f}",
                f"${mr['m_cv8']:,.0f}",
                f"${mr['m_cv9']:,.0f}",
                f"${mr['m_cv10']:,.0f}"
            ]
        })
            st.table(manual_cf_table)
            
            st.divider()
            st.subheader(f'Automatic Valuation Data (Reference) for {ticker_input}')
            
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            with col1:
                st.metric("Current Price", f"${ar['current_price']:.2f}")
            with col2:
                st.metric("Recommended Intrinsic Value", f"${ar['adjusted_value']:.2f}")
            with col3:
                st.metric("Recommended Discount Rate", f"{ar['discount_rate']:.2f}%")
            with col4:
                st.metric("Recommended Growth Rate", f"{ar['expected_growth_rate']:.2f}%")
            with col5:
                st.metric("Recommended Terminal Value", f"${ar['pv_tv_final']:,.0f}")
            with col6:
                st.metric("Recommended Adj. Multiplier", f"{ar['composite_multiplier']:.2f}x")
        else:
            st.error("Error calculating manual valuation. Please try again.")
                           


st.divider()
st.caption(f"Analysis generated {datetime.now().strftime('%Y-%m-%d %H:%M')} HKT")

