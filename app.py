from flask import send_file
import io
from flask import Flask, render_template, request
import pandas as pd

app = Flask(__name__)

# Load dataset once
df = pd.read_csv("final_dashboard_data.csv")
df['llm_explanation'] = df['llm_explanation'].fillna("")

@app.route("/", methods=["GET", "POST"])
def dashboard():
    
    filtered_df = df.copy()
    
    account_id = request.form.get("account_id")
    transaction_id = request.form.get("transaction_id")
    fraud_only = request.form.get("fraud_only")
    if fraud_only:
    	filtered_df = filtered_df[filtered_df["fraud_flag"] == 1]
    
    if account_id:
        filtered_df = filtered_df[filtered_df["account_id"] == account_id]
    
    if transaction_id:
        filtered_df = filtered_df[
            filtered_df["transaction_id"].str.contains(transaction_id, case=False, na=False)
        ]
    
    total_transactions = len(df)
    fraud_count = df["fraud_flag"].sum()
    fraud_percentage = round((fraud_count / total_transactions) * 100, 2)
    # Convert transaction_date to datetime
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    # Filter fraud transactions
    fraud_df = df[df["fraud_flag"] == 1]
    # Group fraud count by date
    fraud_trend = (
        fraud_df
        .groupby(fraud_df["transaction_date"].dt.date)
        .size()
        .reset_index(name="fraud_count")
    )
    # Convert to lists for Chart.js
    trend_dates = fraud_trend["transaction_date"].astype(str).tolist()
    trend_counts = fraud_trend["fraud_count"].tolist()
    # ---------- TOP RISK ACCOUNTS ----------

    top_risk_accounts = (
        df[df["fraud_flag"] == 1]
        .groupby("account_id")
        .size()
        .reset_index(name="fraud_count")
        .sort_values(by="fraud_count", ascending=False)
        .head(5)
    )

    top_accounts = top_risk_accounts.to_dict(orient="records")

    # ---- Risk Level Counts ----
    high_risk = len(filtered_df[filtered_df["fraud_flag"] == 1])

    medium_risk = len(
        filtered_df[
            (filtered_df["fraud_flag"] == 0) &
            (filtered_df["transaction_amount"] > 500)
        ]
    )

    low_risk = len(
        filtered_df[
            (filtered_df["fraud_flag"] == 0) &
            (filtered_df["transaction_amount"] <= 500)
        ]
    )
    # Calculate totals from filtered data
    total = len(filtered_df)
    fraud = filtered_df["fraud_flag"].sum()

    # Prevent division by zero
    if total > 0:
        fraud_rate = round((fraud / total) * 100, 2)
    else:
        fraud_rate = 0

    # Alert logic
    if fraud_rate > 5:
        alert_level = "high"
        alert_message = "⚠️ Elevated Fraud Activity Detected – Immediate Monitoring Recommended."
    else:
        alert_level = "normal"
        alert_message = "✅ System Operating Within Normal Risk Threshold."

    return render_template(
        "dashboard.html",
        tables=filtered_df.to_dict(orient="records"),
        total=total,
        fraud=fraud,
        trend_dates=trend_dates,
        trend_counts=trend_counts,
        top_accounts=top_accounts,
        high_risk=high_risk,
        medium_risk=medium_risk,
        low_risk=low_risk,
        fraud_rate=fraud_rate,
        alert_level=alert_level,
        alert_message=alert_message,
    )
@app.route("/download_fraud_report")
def download_fraud_report():

    # Filter fraud transactions
    fraud_df = df[df["fraud_flag"] == 1]

    # Select important columns
    fraud_report = fraud_df[
        [
            "transaction_id",
            "account_id",
            "transaction_amount",
            "transaction_date",
            "fraud_flag",
            "llm_explanation"
        ]
    ]

    # Create CSV in memory
    output = io.StringIO()
    fraud_report.to_csv(output, index=False)
    output.seek(0)

    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name="fraud_report.csv"
    )
if __name__ == "__main__":
    app.run(debug=True)