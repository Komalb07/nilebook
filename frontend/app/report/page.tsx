"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Navbar from "../components/Navbar";
import { apiUrl } from "../lib/api";
import { useLocalStorageValue } from "../lib/clientStorage";
import { formatDateForCurrency } from "../lib/format";

type YearReport = {
  year: number;
  title: string;
  is_completed_year: boolean;
  is_ongoing_year: boolean;
  summary_label: string;
  total_money_in: number;
  total_money_out: number;
  net_flow: number;
  available_months: number[];
  transaction_count: number;
};

type WeekRange = {
  week: number;
  start_day: number;
  end_day: number;
};

type MonthReport = {
  year: number;
  month: number;
  month_name: string;
  is_completed_month: boolean;
  is_ongoing_month: boolean;
  summary_label: string;
  total_money_in: number;
  total_money_out: number;
  net_flow: number;
  week_ranges: WeekRange[];
  transaction_count: number;
};

type WeekTransaction = {
  id: string;
  raw_text: string;
  date: string;
  amount: number;
  currency: string;
  original_amount?: number | null;
  original_currency?: string | null;
  converted_amount?: number | null;
  converted_currency?: string | null;
  exchange_rate?: number | null;
  exchange_rate_date?: string | null;
  exchange_rate_source?: string | null;
  exchange_rate_fetched_at?: string | null;
  requires_conversion_confirmation?: boolean;
  conversion_error?: string | null;
  sender?: string;
  receiver?: string;
  counterparty?: string;
  category: string;
  transaction_direction: string;
  source: string;
  origin_type: string;
  status?: string;
  is_recurring?: boolean;
  confidence_score?: number;
  review_level?: "none" | "quick" | "full";
  transaction_subject?: string;
  subject_quality?: "clear" | "possibly_typo" | "unclear";
  missing_fields?: string[];
  ambiguity_reasons?: string[];
};

type WeekReport = {
  year: number;
  month: number;
  month_name: string;
  week: number;
  week_label: string;
  start_day: number;
  end_day: number;
  is_completed_week: boolean;
  is_ongoing_week: boolean;
  summary_label: string;
  total_money_in: number;
  total_money_out: number;
  net_flow: number;
  transaction_count: number;
  transactions: WeekTransaction[];
};

type EditableTransaction = {
  id: string;
  raw_text: string;
  date: string;
  amount: number;
  currency: string;
  original_amount: number | null;
  original_currency: string | null;
  converted_amount: number | null;
  converted_currency: string | null;
  exchange_rate: number | null;
  exchange_rate_date: string | null;
  exchange_rate_source: string | null;
  exchange_rate_fetched_at: string | null;
  requires_conversion_confirmation: boolean;
  conversion_error: string | null;
  sender: string;
  receiver: string;
  counterparty: string;
  category: string;
  transaction_direction: string;
  source: string;
  origin_type: string;
  status: string;
  is_recurring: boolean;
  confidence_score: number;
  review_level: "none" | "quick" | "full";
  transaction_subject: string;
  subject_quality: "clear" | "possibly_typo" | "unclear";
  missing_fields: string[];
  ambiguity_reasons: string[];
};

const monthNames: Record<number, string> = {
  1: "January",
  2: "February",
  3: "March",
  4: "April",
  5: "May",
  6: "June",
  7: "July",
  8: "August",
  9: "September",
  10: "October",
  11: "November",
  12: "December",
};

const categories = [
  "grocery",
  "dining",
  "fuel",
  "transport",
  "shopping",
  "subscription",
  "rent",
  "utilities",
  "salary",
  "gift",
  "loan",
  "transfer",
  "health",
  "entertainment",
  "other",
];

const sources = [
  "cash",
  "credit_card",
  "debit_card",
  "checking_account",
  "savings_account",
  "gift_card",
  "other",
];

const directions = [
  "expense",
  "income",
  "transfer",
  "loan_given",
  "loan_received",
  "gift_sent",
  "gift_received",
];

const getErrorMessage = (data: unknown, fallback: string) => {
  const detail =
    data && typeof data === "object" && "detail" in data
      ? (data as { detail?: unknown }).detail
      : undefined;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    return detail
      .map((error: unknown) => {
        if (typeof error === "string") return error;
        if (
          error &&
          typeof error === "object" &&
          "msg" in error &&
          typeof (error as { msg?: unknown }).msg === "string"
        ) {
          return (error as { msg: string }).msg;
        }
        return JSON.stringify(error);
      })
      .join(", ");
  }

  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }

  return fallback;
};

export default function ReportPage() {
  return (
    <Suspense fallback={<ReportLoading />}>
      <ReportPageContent />
    </Suspense>
  );
}

function ReportLoading() {
  return (
    <>
      <Navbar />
      <main style={pageStyle}>
        <section style={heroStyle}>
          <p style={eyebrowStyle}>Finance Report</p>
          <h1 style={titleStyle}>Loading report...</h1>
        </section>
      </main>
    </>
  );
}

function ReportPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const targetTransactionId = searchParams.get("transactionId");
  const currentYear = new Date().getFullYear();

  const userId = useLocalStorageValue("user_id", "__pending__");
  const [selectedYear, setSelectedYear] = useState<number>(currentYear);
  const [yearReport, setYearReport] = useState<YearReport | null>(null);
  const [openMonth, setOpenMonth] = useState<number | null>(null);
  const [openWeek, setOpenWeek] = useState<number | null>(null);
  const [monthReports, setMonthReports] = useState<Record<number, MonthReport>>({});
  const [weekReports, setWeekReports] = useState<Record<string, WeekReport>>({});
  const [message, setMessage] = useState("");
  const [editingTransaction, setEditingTransaction] = useState<EditableTransaction | null>(null);
  const currency = useLocalStorageValue("user_currency", "USD");
  const [availableYears, setAvailableYears] = useState<number[]>([]);

  const getAuthHeaders = () => {
    const token = localStorage.getItem("access_token");

    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    };
  };

  const resetOpenReportState = () => {
    setOpenMonth(null);
    setOpenWeek(null);
    setEditingTransaction(null);
    setMonthReports({});
    setWeekReports({});
  };

  useEffect(() => {
    if (userId === "__pending__") return;

    if (!userId) {
      router.push("/login");
      return;
    }
  }, [router, userId]);

  useEffect(() => {
    if (!targetTransactionId) return;

    const timeout = setTimeout(() => {
      const element = document.getElementById(
        `transaction-${targetTransactionId}`
      );

      if (element) {
        element.scrollIntoView({
          behavior: "smooth",
          block: "center",
        });
      }
    }, 600);

    return () => clearTimeout(timeout);
  }, [targetTransactionId, weekReports]);

  const fetchAvailableYears = async () => {
    if (!userId || userId === "__pending__") return [];

    try {
      const response = await fetch(apiUrl(`/report/${userId}/years`), {
        headers: getAuthHeaders(),
      });
      const data = await response.json();

      if (!response.ok) {
        setMessage(getErrorMessage(data, "Failed to load report years"));
        return [];
      }

      const years = Array.isArray(data.years) ? data.years : [];
      setAvailableYears(years);
      return years;
    } catch {
      setMessage("Failed to load report years");
      return [];
    }
  };

  const fetchYearReport = async (year: number) => {
    if (!userId || userId === "__pending__") return;

    try {
      const response = await fetch(apiUrl(`/report/${userId}/${year}`), {headers: getAuthHeaders(),});
      const data = await response.json();

      if (!response.ok) {
        setMessage(getErrorMessage(data, "Update failed"));
        return;
      }

      setYearReport(data);
      setMessage("");
    } catch {
      setMessage("Failed to load year report");
    }
  };

  const fetchMonthReport = async (
    month: number,
    forceRefresh = false,
    year = selectedYear
  ) => {
    if (!userId || userId === "__pending__") return;
    if (monthReports[month] && !forceRefresh) return;

    try {
      const response = await fetch(apiUrl(`/report/${userId}/${year}/${month}`), {headers: getAuthHeaders(),});
      const data = await response.json();

      if (!response.ok) {
        setMessage(getErrorMessage(data,"Failed to load month report"));
        return;
      }

      setMonthReports((prev) => ({
        ...prev,
        [month]: data,
      }));
      setMessage("");
    } catch {
      setMessage("Failed to load month report");
    }
  };

  const fetchWeekReport = async (
    month: number,
    week: number,
    year = selectedYear
  ) => {
    if (!userId || userId === "__pending__") return;

    const key = `${month}-${week}`;

    try {
      const response = await fetch(apiUrl(`/report/${userId}/${year}/${month}/${week}`), {headers: getAuthHeaders(),});
      const data = await response.json();

      if (!response.ok) {
        setMessage(getErrorMessage(data, "Failed to load week report"));
        return;
      }

      setWeekReports((prev) => ({
        ...prev,
        [key]: data,
      }));
      setMessage("");
    } catch {
      setMessage("Failed to load week report");
    }
  };

  useEffect(() => {
    if (!userId || userId === "__pending__") return;

    const yearParam = searchParams.get("year");
    const monthParam = searchParams.get("month");
    const weekParam = searchParams.get("week");
    const targetMonth = monthParam ? Number(monthParam) : null;
    const targetWeek = weekParam ? Number(weekParam) : null;

    const fetchInitialReport = async () => {
      const years = await fetchAvailableYears();
      const requestedYear = yearParam ? Number(yearParam) : null;
      const targetYear =
        requestedYear && years.includes(requestedYear)
          ? requestedYear
          : years[0];

      if (!targetYear) {
        setYearReport(null);
        setMessage("No transactions found yet.");
        return;
      }

      setSelectedYear(targetYear);
      setEditingTransaction(null);

      await fetchYearReport(targetYear);

      if (targetMonth) {
        setOpenMonth(targetMonth);
        await fetchMonthReport(targetMonth, true, targetYear);
      }

      if (targetMonth && targetWeek) {
        setOpenWeek(targetWeek);
        await fetchWeekReport(targetMonth, targetWeek, targetYear);
      }
    };

    fetchInitialReport();
    // Initial report load should run once when the signed-in user is known.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const refreshCurrentWeekReport = async () => {
    if (openMonth !== null && openWeek !== null) {
      await fetchWeekReport(openMonth, openWeek);
    }
  };

  const changeSelectedYear = async (year: number) => {
    setSelectedYear(year);
    resetOpenReportState();
    await fetchYearReport(year);
  };

  const refreshYearsAndSelectedReport = async () => {
    const years = await fetchAvailableYears();

    if (years.length === 0) {
      setYearReport(null);
      resetOpenReportState();
      setMessage("No transactions found yet.");
      return;
    }

    const nextYear = years.includes(selectedYear) ? selectedYear : years[0];

    if (nextYear !== selectedYear) {
      setSelectedYear(nextYear);
      resetOpenReportState();
    }

    await fetchYearReport(nextYear);
  };

  const toggleMonth = async (month: number) => {
    if (openMonth === month) {
      setOpenMonth(null);
      setOpenWeek(null);
      setEditingTransaction(null);
      return;
    }

    setOpenMonth(month);
    setOpenWeek(null);
    setEditingTransaction(null);
    await fetchMonthReport(month);
  };

  const toggleWeek = async (month: number, week: number) => {
    if (openWeek === week && openMonth === month) {
      setOpenWeek(null);
      setEditingTransaction(null);
      return;
    }

    setOpenWeek(week);
    setEditingTransaction(null);
    await fetchWeekReport(month, week);
  };

  const startEditTransaction = (transaction: WeekTransaction) => {
    setEditingTransaction({
      id: transaction.id,
      raw_text: transaction.raw_text,
      date: transaction.date,
      amount: transaction.amount,
      currency: transaction.currency,
      original_amount: transaction.original_amount ?? null,
      original_currency: transaction.original_currency ?? null,
      converted_amount: transaction.converted_amount ?? null,
      converted_currency: transaction.converted_currency ?? null,
      exchange_rate: transaction.exchange_rate ?? null,
      exchange_rate_date: transaction.exchange_rate_date ?? null,
      exchange_rate_source: transaction.exchange_rate_source ?? null,
      exchange_rate_fetched_at: transaction.exchange_rate_fetched_at ?? null,
      requires_conversion_confirmation:
        transaction.requires_conversion_confirmation ?? false,
      conversion_error: transaction.conversion_error ?? null,
      sender: transaction.sender ?? "Me",
      receiver: transaction.receiver ?? "unknown",
      counterparty: transaction.counterparty ?? "unknown",
      category: transaction.category,
      transaction_direction: transaction.transaction_direction,
      source: transaction.source,
      origin_type: transaction.origin_type,
      status: transaction.status ?? "completed",
      is_recurring: transaction.is_recurring ?? false,
      confidence_score: transaction.confidence_score ?? 0.7,
      review_level: transaction.review_level ?? "full",
      transaction_subject: transaction.transaction_subject ?? "unknown",
      subject_quality: transaction.subject_quality ?? "clear",
      missing_fields: transaction.missing_fields ?? [],
      ambiguity_reasons: transaction.ambiguity_reasons ?? [],
    });
    setMessage("Editing transaction");
  };

  const updateEditField = (
    field: keyof EditableTransaction,
    value: string | number | boolean
  ) => {
    if (!editingTransaction) return;

    setEditingTransaction({
      ...editingTransaction,
      [field]: value,
    });
  };

  const saveEditedTransaction = async () => {
  if (!editingTransaction || !userId || userId === "__pending__") {
    setMessage("Missing transaction or user");
    return;
  }

  const payload = {
    user_id: userId,
    raw_text: String(editingTransaction.raw_text || ""),
    date: editingTransaction.date,
    amount: Number(editingTransaction.amount),
    currency: String(editingTransaction.currency || currency || "USD"),
    original_amount: editingTransaction.original_amount,
    original_currency: editingTransaction.original_currency,
    converted_amount: editingTransaction.converted_amount,
    converted_currency: editingTransaction.converted_currency,
    exchange_rate: editingTransaction.exchange_rate,
    exchange_rate_date: editingTransaction.exchange_rate_date,
    exchange_rate_source: editingTransaction.exchange_rate_source,
    exchange_rate_fetched_at: editingTransaction.exchange_rate_fetched_at,
    requires_conversion_confirmation:
      editingTransaction.requires_conversion_confirmation,
    conversion_error: editingTransaction.conversion_error,
    sender: String(editingTransaction.sender || "Me"),
    receiver: String(editingTransaction.receiver || "unknown"),
    counterparty: String(editingTransaction.counterparty || "unknown"),
    category: String(editingTransaction.category || "other"),
    transaction_direction: String(
      editingTransaction.transaction_direction || "expense"
    ),
    source: String(editingTransaction.source || "other"),
    origin_type: String(editingTransaction.origin_type || "note"),
    status: String(editingTransaction.status || "completed"),
    is_recurring: Boolean(editingTransaction.is_recurring),
    confidence_score: Number(editingTransaction.confidence_score ?? 0.7),
    review_level: editingTransaction.review_level || "full",
    transaction_subject: String(editingTransaction.transaction_subject || "unknown"),
    subject_quality: editingTransaction.subject_quality || "clear",
    missing_fields: editingTransaction.missing_fields || [],
    ambiguity_reasons: editingTransaction.ambiguity_reasons || [],
  };

  try {
    const response = await fetch(
      apiUrl(`/transactions/${editingTransaction.id}`),
      {
        method: "PUT",
        headers: getAuthHeaders(),
        body: JSON.stringify(payload),
      }
    );

    const data = await response.json();

    if (!response.ok) {
      setMessage(
        typeof data.detail === "string"
          ? data.detail
          : JSON.stringify(data.detail || data)
      );
      return;
    }

    setMessage("Transaction updated");
    setEditingTransaction(null);

    await refreshCurrentWeekReport();

    if (openMonth !== null) {
      await fetchMonthReport(openMonth, true);
    }

    await fetchYearReport(selectedYear);
  } catch {
    setMessage("Update failed");
  }
};

  const deleteTransaction = async (transactionId: string) => {
    try {
      const response = await fetch(apiUrl(`/transactions/${transactionId}`), {
        method: "DELETE", headers: getAuthHeaders(), });
      const data = await response.json();

      if (!response.ok) {
        setMessage(getErrorMessage(data, "Delete failed"));
        return;
      }

      setMessage("Transaction deleted");

      if (editingTransaction?.id === transactionId) {
        setEditingTransaction(null);
      }

      await refreshYearsAndSelectedReport();
    } catch {
      setMessage("Delete failed");
    }
  };

  const isMoneyOut = (transaction: WeekTransaction) => {
    return ["expense", "loan_given", "gift_sent"].includes(
      transaction.transaction_direction
    );
  };

  const isMoneyIn = (transaction: WeekTransaction) => {
    return ["income", "loan_received", "gift_received"].includes(
      transaction.transaction_direction
    );
  };

  const formatTransactionAmount = (transaction: WeekTransaction) => {
    const sign = isMoneyOut(transaction) ? "-" : isMoneyIn(transaction) ? "+" : "";
    return `${sign}${transaction.amount.toFixed(2)} ${transaction.currency || currency}`;
  };

  const renderMoney = (amount: number, selectedCurrency = currency) => {
    return `${amount.toFixed(2)} ${selectedCurrency}`;
  };

  const hasConversion = (transaction: WeekTransaction | EditableTransaction) => {
    return Boolean(transaction.original_currency && transaction.exchange_rate);
  };

  const getConversionSummary = (
    transaction: WeekTransaction | EditableTransaction
  ) => {
    if (!hasConversion(transaction)) return "";

    return `${Number(transaction.original_amount ?? 0).toFixed(2)} ${
      transaction.original_currency
    } × ${Number(transaction.exchange_rate).toFixed(4)} = ${Number(
      transaction.amount
    ).toFixed(2)} ${transaction.currency}`;
  };

  const getNetColor = (value: number) => {
    if (value > 0) return "#1f7a45";
    if (value < 0) return "#b42318";
    return "#5d7a66";
  };

  if (!userId || userId === "__pending__") {
    return (
      <>
        <Navbar />
        <main style={pageStyle}>
          <section style={heroStyle}>
            <p style={eyebrowStyle}>Finance Report</p>
            <h1 style={titleStyle}>Redirecting to login...</h1>
          </section>
        </main>
      </>
    );
  }

  return (
    <>
      <Navbar />

      <main style={pageStyle}>
        <section style={heroStyle}>
          <p style={eyebrowStyle}>Reports</p>
          <h1 style={titleStyle}>Finance Report</h1>
          <p style={subtitleStyle}>
            Review your money flow by year, month, and week. Expand each section to inspect and correct transactions.
          </p>
        </section>

        <section style={reportShellStyle}>
          <div style={topBarStyle}>
            <div>
              <h2 style={cardTitleStyle}>{selectedYear} Overview</h2>
              <p style={cardSubtitleStyle}>Annual summary and monthly breakdown</p>
            </div>

            <label style={yearPickerStyle}>
              <span style={fieldLabelStyle}>Year</span>
              <select
                value={selectedYear}
                onChange={(e) => changeSelectedYear(Number(e.target.value))}
                disabled={availableYears.length === 0}
                style={yearInputStyle}
              >
                {availableYears.map((year) => (
                  <option key={year} value={year}>
                    {year}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {message && <div style={messageStyle}>{message}</div>}

          {yearReport && (
            <div style={summaryCardStyle}>
              <div style={summaryHeaderStyle}>
                <div>
                  <p style={eyebrowStyle}>{yearReport.is_ongoing_year ? "So far" : "Completed year"}</p>
                  <h3 style={sectionTitleStyle}>{yearReport.title}</h3>
                </div>

                <span style={transactionCountBadgeStyle}>
                  {yearReport.transaction_count} transactions
                </span>
              </div>

              {yearReport.summary_label && (
                <p style={summaryNoteStyle}>{yearReport.summary_label}</p>
              )}

              <div style={moneyGridStyle}>
                <MoneyCard
                  label="Total money in"
                  value={renderMoney(yearReport.total_money_in)}
                  tone="positive"
                />
                <MoneyCard
                  label="Total money out"
                  value={renderMoney(yearReport.total_money_out)}
                  tone="negative"
                />
                <MoneyCard
                  label="Net flow"
                  value={renderMoney(yearReport.net_flow)}
                  customColor={getNetColor(yearReport.net_flow)}
                />
              </div>
            </div>
          )}

          {yearReport && yearReport.available_months.length === 0 && (
            <div style={emptyStateStyle}>No transactions found for this year.</div>
          )}

          {yearReport && yearReport.available_months.length > 0 && (
            <div style={monthsContainerStyle}>
              {yearReport.available_months.map((month) => {
                const monthReport = monthReports[month];
                const isMonthOpen = openMonth === month;

                return (
                  <div key={month} style={monthBoxStyle}>
                    <button
                      onClick={() => toggleMonth(month)}
                      style={monthButtonStyle}
                    >
                      <span>{monthNames[month]}</span>
                      <span style={monthChevronStyle}>{isMonthOpen ? "−" : "+"}</span>
                    </button>

                    {isMonthOpen && monthReport && (
                      <div style={monthContentStyle}>
                        {monthReport.summary_label && (
                          <p style={summaryNoteStyle}>{monthReport.summary_label}</p>
                        )}

                        <div style={moneyGridStyle}>
                          <MoneyCard
                            label="Money in"
                            value={renderMoney(monthReport.total_money_in)}
                            tone="positive"
                          />
                          <MoneyCard
                            label="Money out"
                            value={renderMoney(monthReport.total_money_out)}
                            tone="negative"
                          />
                          <MoneyCard
                            label="Net flow"
                            value={renderMoney(monthReport.net_flow)}
                            customColor={getNetColor(monthReport.net_flow)}
                          />
                        </div>

                        <div style={weeksContainerStyle}>
                          {monthReport.week_ranges.map((weekRange) => {
                            const weekKey = `${month}-${weekRange.week}`;
                            const weekReport = weekReports[weekKey];
                            const isWeekOpen = openMonth === month && openWeek === weekRange.week;

                            return (
                              <div key={weekKey} style={weekBoxStyle}>
                                <button
                                  onClick={() => toggleWeek(month, weekRange.week)}
                                  style={weekButtonStyle}
                                >
                                  <span>
                                    Week {weekRange.week} ({weekRange.start_day} - {weekRange.end_day})
                                  </span>
                                  <span>{isWeekOpen ? "−" : "+"}</span>
                                </button>

                                {isWeekOpen && weekReport && (
                                  <div style={weekContentStyle}>
                                    {weekReport.summary_label && (
                                      <p style={summaryNoteStyle}>{weekReport.summary_label}</p>
                                    )}

                                    <div style={moneyGridStyle}>
                                      <MoneyCard
                                        label="Money in"
                                        value={renderMoney(weekReport.total_money_in)}
                                        tone="positive"
                                      />
                                      <MoneyCard
                                        label="Money out"
                                        value={renderMoney(weekReport.total_money_out)}
                                        tone="negative"
                                      />
                                      <MoneyCard
                                        label="Net flow"
                                        value={renderMoney(weekReport.net_flow)}
                                        customColor={getNetColor(weekReport.net_flow)}
                                      />
                                    </div>

                                    <div style={transactionSectionStyle}>
                                      <div style={transactionHeaderStyle}>
                                        <div>
                                          <p style={eyebrowStyle}>Transactions</p>
                                          <h4 style={sectionTitleStyle}>{weekReport.week_label}</h4>
                                        </div>
                                        <span style={transactionCountBadgeStyle}>
                                          {weekReport.transaction_count} items
                                        </span>
                                      </div>

                                      {weekReport.transactions.length === 0 ? (
                                        <p style={emptyStateStyle}>No transactions in this week.</p>
                                      ) : (
                                        <div style={transactionListStyle}>
                                          {weekReport.transactions.map((t) => (
                                            <div
                                              key={t.id}
                                              id={`transaction-${t.id}`}
                                              style={{
                                                ...transactionRowStyle,
                                                border:
                                                  targetTransactionId === t.id
                                                    ? "2px solid #1f7a45"
                                                    : transactionRowStyle.border,
                                                background:
                                                  targetTransactionId === t.id
                                                    ? "#f0f8f2"
                                                    : transactionRowStyle.background,
                                              }}
                                            >
                                              <div style={transactionMainStyle}>
                                                <strong style={transactionDescriptionStyle}>{t.raw_text}</strong>
                                                <p style={transactionMetaStyle}>
                                                  {formatDateForCurrency(t.date, currency)} • {t.category} • {t.source} • {t.origin_type}
                                                  {hasConversion(t)
                                                    ? ` • ${getConversionSummary(t)}`
                                                    : ""}
                                                </p>
                                              </div>

                                              <div style={transactionRightStyle}>
                                                <strong
                                                  style={{
                                                    ...transactionAmountStyle,
                                                    color: isMoneyOut(t)
                                                      ? "#b42318"
                                                      : isMoneyIn(t)
                                                        ? "#1f7a45"
                                                        : "#5d7a66",
                                                  }}
                                                >
                                                  {formatTransactionAmount(t)}
                                                </strong>
                                                {t.origin_type !== "recurring" && (
                                                  <div style={smallButtonRowStyle}>
                                                    <button
                                                      onClick={() => startEditTransaction(t)}
                                                      style={smallSecondaryButtonStyle}
                                                    >
                                                      Edit
                                                    </button>
                                                    <button
                                                      onClick={() => deleteTransaction(t.id)}
                                                      style={dangerButtonStyle}
                                                    >
                                                      Delete
                                                    </button>
                                                  </div>
                                                )}
                                              </div>
                                            </div>
                                          ))}
                                        </div>
                                      )}

                                      {editingTransaction && (
                                        <div style={editBoxStyle}>
                                          <div style={editHeaderStyle}>
                                            <div>
                                              <p style={eyebrowStyle}>Edit</p>
                                              <h4 style={sectionTitleStyle}>Edit Transaction</h4>
                                            </div>
                                          </div>

                                          <div style={editGridStyle}>
                                            <Field label="Description">
                                              <input
                                                value={editingTransaction.raw_text}
                                                onChange={(e) => updateEditField("raw_text", e.target.value)}
                                                style={inputStyle}
                                              />
                                            </Field>

                                            <Field label="Date">
                                              <input
                                                type="date"
                                                value={editingTransaction.date}
                                                onChange={(e) => updateEditField("date", e.target.value)}
                                                style={inputStyle}
                                              />
                                            </Field>

                                            <Field label="Amount">
                                              <input
                                                type="number"
                                                step="0.01"
                                                value={editingTransaction.amount}
                                                onChange={(e) => updateEditField("amount", Number(e.target.value))}
                                                style={inputStyle}
                                              />
                                            </Field>

                                            <Field label="Currency">
                                              <input
                                                value={editingTransaction.currency}
                                                onChange={(e) => updateEditField("currency", e.target.value)}
                                                style={inputStyle}
                                              />
                                            </Field>

                                            {hasConversion(editingTransaction) && (
                                              <Field label="Conversion">
                                                <input
                                                  value={getConversionSummary(editingTransaction)}
                                                  readOnly
                                                  style={inputStyle}
                                                />
                                              </Field>
                                            )}

                                            <Field label="Sender">
                                              <input
                                                value={editingTransaction.sender}
                                                onChange={(e) => updateEditField("sender", e.target.value)}
                                                style={inputStyle}
                                              />
                                            </Field>

                                            <Field label="Receiver">
                                              <input
                                                value={editingTransaction.receiver}
                                                onChange={(e) => updateEditField("receiver", e.target.value)}
                                                style={inputStyle}
                                              />
                                            </Field>

                                            <Field label="Counterparty">
                                              <input
                                                value={editingTransaction.counterparty}
                                                onChange={(e) => updateEditField("counterparty", e.target.value)}
                                                style={inputStyle}
                                              />
                                            </Field>

                                            <Field label="Category">
                                              <select
                                                value={editingTransaction.category}
                                                onChange={(e) => updateEditField("category", e.target.value)}
                                                style={inputStyle}
                                              >
                                                {categories.map((c) => (
                                                  <option key={c} value={c}>{c}</option>
                                                ))}
                                              </select>
                                            </Field>

                                            <Field label="Direction">
                                              <select
                                                value={editingTransaction.transaction_direction}
                                                onChange={(e) => updateEditField("transaction_direction", e.target.value)}
                                                style={inputStyle}
                                              >
                                                {directions.map((d) => (
                                                  <option key={d} value={d}>{d}</option>
                                                ))}
                                              </select>
                                            </Field>

                                            <Field label="Source">
                                              <select
                                                value={editingTransaction.source}
                                                onChange={(e) => updateEditField("source", e.target.value)}
                                                style={inputStyle}
                                              >
                                                {sources.map((s) => (
                                                  <option key={s} value={s}>{s}</option>
                                                ))}
                                              </select>
                                            </Field>

                                            <Field label="Origin">
                                              <input
                                                value={editingTransaction.origin_type}
                                                onChange={(e) => updateEditField("origin_type", e.target.value)}
                                                style={inputStyle}
                                              />
                                            </Field>

                                            <Field label="Status">
                                              <input
                                                value={editingTransaction.status}
                                                onChange={(e) => updateEditField("status", e.target.value)}
                                                style={inputStyle}
                                              />
                                            </Field>

                                            <Field label="Review Level">
                                              <select
                                                value={editingTransaction.review_level}
                                                onChange={(e) =>
                                                  updateEditField(
                                                    "review_level",
                                                    e.target.value as "none" | "quick" | "full"
                                                  )
                                                }
                                                style={inputStyle}
                                              >
                                                <option value="none">none</option>
                                                <option value="quick">quick</option>
                                                <option value="full">full</option>
                                              </select>
                                            </Field>

                                            <label style={checkboxLabelStyle}>
                                              <input
                                                type="checkbox"
                                                checked={editingTransaction.is_recurring}
                                                onChange={(e) => updateEditField("is_recurring", e.target.checked)}
                                              />
                                              Recurring transaction
                                            </label>
                                          </div>

                                          <div style={actionRowStyle}>
                                            <button onClick={saveEditedTransaction} style={primaryButtonStyle}>
                                              Save Changes
                                            </button>
                                            <button
                                              onClick={() => setEditingTransaction(null)}
                                              style={secondaryButtonStyle}
                                            >
                                              Cancel
                                            </button>
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </main>
    </>
  );
}

function MoneyCard({
  label,
  value,
  tone,
  customColor,
}: {
  label: string;
  value: string;
  tone?: "positive" | "negative";
  customColor?: string;
}) {
  const color = customColor || (tone === "negative" ? "#b42318" : "#1f7a45");

  return (
    <div style={moneyCardStyle}>
      <span style={moneyLabelStyle}>{label}</span>
      <strong style={{ ...moneyValueStyle, color }}>{value}</strong>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label style={fieldStyle}>
      <span style={fieldLabelStyle}>{label}</span>
      {children}
    </label>
  );
}

const pageStyle: React.CSSProperties = {
  minHeight: "100vh",
  padding: "2rem",
  background: "linear-gradient(180deg, #f7fbf7 0%, #eef5ef 100%)",
  color: "#17351f",
};

const heroStyle: React.CSSProperties = {
  maxWidth: "1080px",
  margin: "0 auto 1.5rem auto",
};

const eyebrowStyle: React.CSSProperties = {
  margin: 0,
  fontSize: "0.78rem",
  letterSpacing: "0.08em",
  textTransform: "uppercase",
  color: "#5d7a66",
  fontWeight: 700,
};

const titleStyle: React.CSSProperties = {
  margin: "0.25rem 0",
  fontSize: "2rem",
  lineHeight: 1.15,
  color: "#14351f",
};

const subtitleStyle: React.CSSProperties = {
  margin: 0,
  color: "#5b6f60",
  maxWidth: "720px",
  lineHeight: 1.6,
};

const reportShellStyle: React.CSSProperties = {
  width: "100%",
  maxWidth: "1080px",
  margin: "0 auto",
  border: "1px solid #d8e7db",
  borderRadius: "22px",
  padding: "1.5rem",
  background: "rgba(255, 255, 255, 0.92)",
  boxShadow: "0 22px 60px rgba(35, 79, 48, 0.10)",
};

const topBarStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "1rem",
  alignItems: "flex-start",
  marginBottom: "1rem",
};

const cardTitleStyle: React.CSSProperties = {
  margin: 0,
  color: "#14351f",
  fontSize: "1.35rem",
};

const cardSubtitleStyle: React.CSSProperties = {
  margin: "0.25rem 0 0 0",
  color: "#667c6b",
};

const yearPickerStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "0.35rem",
  minWidth: "120px",
};

const yearInputStyle: React.CSSProperties = {
  padding: "0.65rem 0.75rem",
  borderRadius: "12px",
  border: "1px solid #cfded2",
  color: "#17351f",
  outline: "none",
};

const messageStyle: React.CSSProperties = {
  marginTop: "1rem",
  marginBottom: "1rem",
  padding: "0.8rem 1rem",
  background: "#f0f8f2",
  border: "1px solid #cfe6d5",
  borderRadius: "14px",
  color: "#225b34",
  fontWeight: 700,
};

const summaryCardStyle: React.CSSProperties = {
  border: "1px solid #d7e7da",
  borderRadius: "18px",
  padding: "1.2rem",
  background: "#fbfdfb",
  marginBottom: "1.25rem",
};

const summaryHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "1rem",
  alignItems: "center",
  marginBottom: "1rem",
};

const sectionTitleStyle: React.CSSProperties = {
  margin: "0.2rem 0 0 0",
  color: "#17351f",
};

const transactionCountBadgeStyle: React.CSSProperties = {
  padding: "0.45rem 0.65rem",
  borderRadius: "999px",
  background: "#eaf7ee",
  border: "1px solid #c8e8d2",
  color: "#1f6b3c",
  fontWeight: 800,
  fontSize: "0.82rem",
  whiteSpace: "nowrap",
};

const summaryNoteStyle: React.CSSProperties = {
  margin: "0 0 1rem 0",
  color: "#5b6f60",
  fontStyle: "italic",
};

const moneyGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
  gap: "0.75rem",
};

const moneyCardStyle: React.CSSProperties = {
  padding: "0.95rem",
  border: "1px solid #e2ece4",
  borderRadius: "15px",
  background: "#ffffff",
};

const moneyLabelStyle: React.CSSProperties = {
  display: "block",
  color: "#6a7f70",
  fontSize: "0.78rem",
  marginBottom: "0.25rem",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  fontWeight: 700,
};

const moneyValueStyle: React.CSSProperties = {
  fontSize: "1.15rem",
  fontWeight: 900,
};

const emptyStateStyle: React.CSSProperties = {
  padding: "1rem",
  borderRadius: "14px",
  background: "#f7fbf7",
  color: "#6b7d70",
};

const monthsContainerStyle: React.CSSProperties = {
  display: "grid",
  gap: "0.85rem",
};

const monthBoxStyle: React.CSSProperties = {
  border: "1px solid #d8e7db",
  borderRadius: "17px",
  background: "#ffffff",
  overflow: "hidden",
};

const monthButtonStyle: React.CSSProperties = {
  width: "100%",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  border: "none",
  background: "#ffffff",
  color: "#17351f",
  fontWeight: 900,
  fontSize: "1rem",
  padding: "1rem",
  cursor: "pointer",
};

const monthChevronStyle: React.CSSProperties = {
  color: "#1f7a45",
  fontSize: "1.2rem",
};

const monthContentStyle: React.CSSProperties = {
  borderTop: "1px solid #e1ebe3",
  padding: "1rem",
  background: "#fbfdfb",
};

const weeksContainerStyle: React.CSSProperties = {
  display: "grid",
  gap: "0.75rem",
  marginTop: "1rem",
};

const weekBoxStyle: React.CSSProperties = {
  border: "1px solid #e3ece5",
  borderRadius: "15px",
  background: "#ffffff",
  overflow: "hidden",
};

const weekButtonStyle: React.CSSProperties = {
  width: "100%",
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  border: "none",
  background: "#ffffff",
  color: "#294c32",
  fontWeight: 800,
  padding: "0.85rem 1rem",
  cursor: "pointer",
};

const weekContentStyle: React.CSSProperties = {
  borderTop: "1px solid #e1ebe3",
  padding: "1rem",
  background: "#fffefd",
};

const transactionSectionStyle: React.CSSProperties = {
  marginTop: "1.1rem",
  paddingTop: "1rem",
  borderTop: "1px solid #e7eee8",
};

const transactionHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "1rem",
  alignItems: "center",
  marginBottom: "0.9rem",
};

const transactionListStyle: React.CSSProperties = {
  display: "grid",
  gap: "0.75rem",
};

const transactionRowStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "1rem",
  padding: "0.9rem",
  border: "1px solid #e2ece4",
  borderRadius: "14px",
  background: "#ffffff",
};

const transactionMainStyle: React.CSSProperties = {
  minWidth: 0,
};

const transactionDescriptionStyle: React.CSSProperties = {
  color: "#17351f",
  fontSize: "0.95rem",
  wordBreak: "break-word",
};

const transactionMetaStyle: React.CSSProperties = {
  margin: "0.25rem 0 0 0",
  color: "#6a7f70",
  fontSize: "0.82rem",
};

const transactionRightStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "flex-end",
  flexDirection: "column",
  gap: "0.5rem",
  whiteSpace: "nowrap",
};

const transactionAmountStyle: React.CSSProperties = {
  color: "#1f7a45",
  fontWeight: 900,
};

const smallButtonRowStyle: React.CSSProperties = {
  display: "flex",
  gap: "0.4rem",
};

const smallSecondaryButtonStyle: React.CSSProperties = {
  border: "1px solid #c8d9cc",
  borderRadius: "999px",
  padding: "0.4rem 0.65rem",
  background: "#ffffff",
  color: "#245034",
  fontWeight: 800,
  cursor: "pointer",
};

const dangerButtonStyle: React.CSSProperties = {
  border: "1px solid #f2c7c3",
  borderRadius: "999px",
  padding: "0.4rem 0.65rem",
  background: "#fff5f4",
  color: "#b42318",
  fontWeight: 800,
  cursor: "pointer",
};

const editBoxStyle: React.CSSProperties = {
  border: "1px solid #e5d8c6",
  borderRadius: "18px",
  padding: "1.2rem",
  marginTop: "1rem",
  background: "#fffdf9",
};

const editHeaderStyle: React.CSSProperties = {
  marginBottom: "1rem",
};

const editGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
  gap: "0.9rem",
  marginBottom: "1rem",
};

const fieldStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "0.35rem",
};

const fieldLabelStyle: React.CSSProperties = {
  fontWeight: 800,
  color: "#294c32",
  fontSize: "0.86rem",
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "0.72rem 0.8rem",
  borderRadius: "12px",
  border: "1px solid #cfded2",
  background: "#ffffff",
  color: "#17351f",
  outline: "none",
};

const checkboxLabelStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "0.5rem",
  fontWeight: 700,
  color: "#294c32",
  paddingTop: "1.6rem",
};

const actionRowStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "0.75rem",
  flexWrap: "wrap",
};

const primaryButtonStyle: React.CSSProperties = {
  border: "none",
  borderRadius: "999px",
  padding: "0.75rem 1.1rem",
  background: "#1f7a45",
  color: "white",
  fontWeight: 800,
  cursor: "pointer",
  boxShadow: "0 10px 24px rgba(31, 122, 69, 0.22)",
};

const secondaryButtonStyle: React.CSSProperties = {
  border: "1px solid #c8d9cc",
  borderRadius: "999px",
  padding: "0.72rem 1rem",
  background: "#ffffff",
  color: "#245034",
  fontWeight: 800,
  cursor: "pointer",
};
