"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "../components/Navbar";
import { apiUrl } from "../lib/api";
import { useLocalStorageValue, useSessionStorageValue } from "../lib/clientStorage";
import { formatDateForCurrency } from "../lib/format";

const categories = [
  "grocery", "dining", "fuel", "transport", "shopping", "subscription",
  "rent", "utilities", "salary", "gift", "loan", "transfer",
  "health", "entertainment", "other",
];

const sources = [
  "cash", "credit_card", "debit_card", "checking_account",
  "savings_account", "gift_card", "other",
];

const directions = [
  "expense", "income", "transfer", "loan_given",
  "loan_received", "gift_sent", "gift_received",
];

type RecurringFrequency =
  | "none"
  | "weekly"
  | "biweekly"
  | "monthly"
  | "yearly"
  | "custom_days";

type ParsedTransaction = {
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

  recurring_frequency: RecurringFrequency;
  recurring_interval_days: number | null;
  recurring_action: "none" | "create" | "cancel";

  confidence_score: number;

  transaction_subject: string;
  subject_quality: "clear" | "possibly_typo" | "unclear";

  missing_fields: string[];
  ambiguity_reasons: string[];

  review_level: "none" | "quick" | "full";
};

type ParsedTransactionBatch = {
  transactions: Partial<ParsedTransaction>[];
  message?: string;
};

type Transaction = {
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
  category: string;
  transaction_direction: string;
  source: string;
};

type RecurringCancelMatch = {
  id: string;
  name: string;
  amount: number;
  currency: string;
  category: string;
  frequency: string;
  start_date: string;
  score: number;
};

export default function DashboardPage() {
  const router = useRouter();

  const [note, setNote] = useState("");
  const userId = useLocalStorageValue("user_id", "__pending__");
  const [message, setMessage] = useState("");
  const [parsedData, setParsedData] = useState<ParsedTransaction | null>(null);

  const firstName = useLocalStorageValue("user_first_name");
  const shouldShowWelcome = useSessionStorageValue("show_welcome") === "true";
  const [welcomeDismissed, setWelcomeDismissed] = useState(false);
  const showWelcome = shouldShowWelcome && !welcomeDismissed;
  const [animateWelcome, setAnimateWelcome] = useState(false);
  const [isParsing, setIsParsing] = useState(false);
  const currency = useLocalStorageValue("user_currency", "USD");

  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [isParseHovered, setIsParseHovered] = useState(false);
  const [pendingCancellationMatches, setPendingCancellationMatches] = useState<
    RecurringCancelMatch[]
  >([]);

  const getAuthHeaders = () => {
    const token = localStorage.getItem("access_token");

    return {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    };
  };

  useEffect(() => {
    if (userId === "__pending__") return;

    if (!userId) {
      router.push("/login");
      return;
    }
  }, [router, userId]);

  useEffect(() => {
    if (showWelcome) {
      setTimeout(() => {
        setAnimateWelcome(true);
      }, 150);

      setTimeout(() => {
        setWelcomeDismissed(true);
        setAnimateWelcome(false);
        sessionStorage.removeItem("show_welcome");
      }, 2200);
    }
  }, [showWelcome]);

  const normalizeParsedData = (data: Partial<ParsedTransaction>): ParsedTransaction => {
    return {
      raw_text: data.raw_text || note,
      date: data.date || new Date().toISOString().slice(0, 10),

      amount: Number(data.amount ?? 0),

      currency: data.currency || currency || "USD",
      original_amount:
        data.original_amount === null ||
        data.original_amount === undefined
          ? null
          : Number(data.original_amount),
      original_currency: data.original_currency || null,
      converted_amount:
        data.converted_amount === null ||
        data.converted_amount === undefined
          ? null
          : Number(data.converted_amount),
      converted_currency: data.converted_currency || null,
      exchange_rate:
        data.exchange_rate === null ||
        data.exchange_rate === undefined
          ? null
          : Number(data.exchange_rate),
      exchange_rate_date: data.exchange_rate_date || null,
      exchange_rate_source: data.exchange_rate_source || null,
      exchange_rate_fetched_at: data.exchange_rate_fetched_at || null,
      requires_conversion_confirmation: Boolean(
        data.requires_conversion_confirmation ?? false
      ),
      conversion_error: data.conversion_error || null,

      sender: data.sender || "unknown",
      receiver: data.receiver || "unknown",
      counterparty: data.counterparty || "unknown",

      category: data.category || "other",

      transaction_direction:
        data.transaction_direction || "expense",

      source: data.source || "other",

      origin_type: data.origin_type || "note",

      status: data.status || "completed",

      is_recurring: Boolean(data.is_recurring ?? false),

      recurring_frequency:
        data.recurring_frequency === "weekly" ||
        data.recurring_frequency === "biweekly" ||
        data.recurring_frequency === "monthly" ||
        data.recurring_frequency === "yearly" ||
        data.recurring_frequency === "custom_days" ||
        data.recurring_frequency === "none"
          ? data.recurring_frequency
          : "none",

      recurring_interval_days:
        data.recurring_interval_days === null ||
        data.recurring_interval_days === undefined
          ? null
          : Number(data.recurring_interval_days),

      recurring_action:
        data.recurring_action === "create" ||
        data.recurring_action === "cancel" ||
        data.recurring_action === "none"
          ? data.recurring_action
          : "none",

      confidence_score: Number(data.confidence_score ?? 0.6),

      transaction_subject:
        data.transaction_subject || "unknown",

      subject_quality:
        data.subject_quality === "clear" ||
        data.subject_quality === "possibly_typo" ||
        data.subject_quality === "unclear"
          ? data.subject_quality
          : "unclear",

      missing_fields: Array.isArray(data.missing_fields)
        ? data.missing_fields
        : [],

      ambiguity_reasons: Array.isArray(data.ambiguity_reasons)
        ? data.ambiguity_reasons
        : [],

      review_level:
        data.review_level === "none" ||
        data.review_level === "quick" ||
        data.review_level === "full"
          ? data.review_level
          : "full",
    };
  };

  const getDateParts = (dateString: string) => {
    const [year, month, day] = dateString.split("-").map(Number);
    return { year, month, day };
  };

  const formatLocalDate = (dateString: string) => {
    return formatDateForCurrency(dateString, currency);
  };

  const hasConversion = (transaction: ParsedTransaction | Transaction) => {
    return Boolean(transaction.original_currency && transaction.exchange_rate);
  };

  const getConversionSummary = (transaction: ParsedTransaction | Transaction) => {
    if (!hasConversion(transaction)) return "";

    return `${Number(transaction.original_amount ?? 0).toFixed(2)} ${
      transaction.original_currency
    } × ${Number(transaction.exchange_rate).toFixed(4)} = ${Number(
      transaction.amount
    ).toFixed(2)} ${transaction.currency}`;
  };

  const getConversionRateSummary = (
    transaction: ParsedTransaction | Transaction
  ) => {
    if (!hasConversion(transaction)) return "";

    const rateDate = transaction.exchange_rate_date
      ? formatDateForCurrency(transaction.exchange_rate_date, currency)
      : "today";

    return `As per ${rateDate}, the exchange rate is 1 ${transaction.original_currency} = ${Number(
      transaction.exchange_rate
    ).toFixed(4)} ${transaction.currency}`;
  };

  const getRecurringTimeFrame = (transaction: ParsedTransaction) => {
    const startDate = formatLocalDate(transaction.date);

    if (transaction.recurring_frequency === "custom_days") {
      const intervalDays = transaction.recurring_interval_days || 1;
      return `Every ${intervalDays} days starting ${startDate}`;
    }

    if (transaction.recurring_frequency === "biweekly") {
      return `Every 2 weeks starting ${startDate}`;
    }

    if (transaction.recurring_frequency === "weekly") {
      return `Weekly starting ${startDate}`;
    }

    if (transaction.recurring_frequency === "monthly") {
      return `Monthly on day ${getDateParts(transaction.date).day}, starting ${startDate}`;
    }

    if (transaction.recurring_frequency === "yearly") {
      return `Yearly starting ${startDate}`;
    }

    return `Monthly on day ${getDateParts(transaction.date).day}, starting ${startDate}`;
  };

  const createRecurringRule = async (
    transaction: ParsedTransaction,
    transactionId: string | null = null
    ) => {
    if (!userId || userId === "__pending__") {
      setMessage("Missing user. Please log in again.");
      return false;
    }

    const recurringName =
      transaction.counterparty !== "unknown"
        ? transaction.counterparty
        : transaction.transaction_subject;

    try {
      const response = await fetch(apiUrl("/recurring-transactions"), {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          user_id: userId,
          name: recurringName,
          amount: transaction.amount,
          currency: transaction.currency,
          original_amount: transaction.original_amount,
          original_currency: transaction.original_currency,
          exchange_rate: transaction.exchange_rate,
          exchange_rate_date: transaction.exchange_rate_date,
          exchange_rate_source: transaction.exchange_rate_source,
          exchange_rate_fetched_at: transaction.exchange_rate_fetched_at,
          category: transaction.category,
          transaction_direction: transaction.transaction_direction,
          source: transaction.source,
          frequency:
            transaction.recurring_frequency === "none"
              ? "monthly"
              : transaction.recurring_frequency,
          interval_days: transaction.recurring_interval_days,
          start_date: transaction.date,
          due_day: String(getDateParts(transaction.date).day),
          created_from_transaction_id: transactionId,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        setMessage(data.detail || "Recurring rule creation failed");
        return false;
      }

      return true;
    } catch {
      setMessage("Could not create recurring rule.");
      return false;
    }
  };

  const saveOnceOnly = async () => {
    if (!parsedData || !userId || userId === "__pending__") return;

    const oneTimeTransaction = {
      ...parsedData,
      is_recurring: false,
      recurring_action: "none" as const,
      recurring_frequency: "none" as const,
      recurring_interval_days: null,
    };

    const saved = await saveTransactionDirect(oneTimeTransaction);

    if (saved) {
      setMessage("Transaction saved once.");
      setParsedData(null);
      setNote("");
      fetchTransactions(userId);
    }
  };

  const saveAsRecurring = async () => {
    if (!parsedData || !userId || userId === "__pending__") return;

    const savedTransactionId = await saveTransactionDirect({
      ...parsedData,
      is_recurring: true,
    });

    if (!savedTransactionId) return;

    const recurringCreated = await createRecurringRule(
      parsedData,
      typeof savedTransactionId === "string" ? savedTransactionId : null
    );

    if (recurringCreated) {
      setMessage("Transaction saved and recurring rule created.");
      setParsedData(null);
      setNote("");
      fetchTransactions(userId);
    }
  };

  const cancelRecurringRule = async () => {
    if (!parsedData || !userId || userId === "__pending__") return;

    const recurringName =
      parsedData.counterparty !== "unknown"
        ? parsedData.counterparty
        : parsedData.transaction_subject;

    try {
      const response = await fetch(
        apiUrl("/recurring-transactions/cancel"),
        {
          method: "POST",
          headers: getAuthHeaders(),
          body: JSON.stringify({
            user_id: userId,
            name: recurringName,
            cancel_date: parsedData.date,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        setMessage(data.detail || "Could not cancel recurring payment.");
        return;
      }

      if (data.requires_confirmation) {
        setPendingCancellationMatches(data.possible_matches || []);
        setMessage("Select the recurring item to cancel.");
        return;
      }

      setMessage("Recurring payment cancelled.");
      setPendingCancellationMatches([]);
      setParsedData(null);
      setNote("");
    } catch {
      setMessage("Could not connect to backend.");
    }
  };

  const confirmRecurringCancellationMatch = async (recurringId: string) => {
    if (!parsedData || !userId || userId === "__pending__") return;

    try {
      const response = await fetch(
        apiUrl(`/recurring-transactions/${recurringId}/confirm-cancel`),
        {
          method: "POST",
          headers: getAuthHeaders(),
          body: JSON.stringify({
            user_id: userId,
            cancel_date: parsedData.date,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        setMessage(data.detail || "Could not confirm cancellation.");
        return;
      }

      setMessage("Recurring payment cancelled.");
      setPendingCancellationMatches([]);
      setParsedData(null);
      setNote("");
    } catch {
      setMessage("Could not connect to backend.");
    }
  };

  const saveTransactionDirect = async (
    transaction: ParsedTransaction
  ) => {
    if (!userId || userId === "__pending__") {
      setMessage("Missing user. Please log in again.");
      return false;
    }

    try {
      const response = await fetch(
        apiUrl("/transactions"),
        {
          method: "POST",
          headers: getAuthHeaders(),
          body: JSON.stringify({
            user_id: userId,

            raw_text: transaction.raw_text,
            date: transaction.date,
            amount: transaction.amount,
            currency: transaction.currency,
            original_amount: transaction.original_amount,
            original_currency: transaction.original_currency,
            converted_amount: transaction.converted_amount,
            converted_currency: transaction.converted_currency,
            exchange_rate: transaction.exchange_rate,
            exchange_rate_date: transaction.exchange_rate_date,
            exchange_rate_source: transaction.exchange_rate_source,
            exchange_rate_fetched_at: transaction.exchange_rate_fetched_at,
            requires_conversion_confirmation:
              transaction.requires_conversion_confirmation,
            conversion_error: transaction.conversion_error,

            sender: transaction.sender,
            receiver: transaction.receiver,
            counterparty: transaction.counterparty,

            category: transaction.category,
            transaction_direction:
              transaction.transaction_direction,

            source: transaction.source,
            origin_type: transaction.origin_type,

            status: transaction.status,
            is_recurring: transaction.is_recurring,

            confidence_score:
              transaction.confidence_score,

            transaction_subject:
              transaction.transaction_subject,

            subject_quality:
              transaction.subject_quality,

            missing_fields:
              transaction.missing_fields,

            ambiguity_reasons:
              transaction.ambiguity_reasons,

            review_level: transaction.review_level,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        setMessage(data.detail || "Auto-save failed");
        return false;
      }

      return data.transaction_id || true;
    } catch {
      setMessage("Could not connect to backend");
      return false;
    }
  };

  const fetchTransactions = async (currentUserId: string) => {
    try {
      const response = await fetch(
        apiUrl(`/transactions/${currentUserId}`),
        {
          headers: getAuthHeaders(),
        }
      );
      const data = await response.json();

      if (!response.ok) {
        setMessage(data.detail || "Failed to load transactions");
        return;
      }

      setTransactions(data.slice(0, 5));
    } catch {
      setMessage("Could not load recent transactions");
    }
  };

  useEffect(() => {
    if (!userId || userId === "__pending__") return;
    fetchTransactions(userId);
    // Fetch once for the signed-in user on page load.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const parseNote = async () => {
    if (!note.trim()) {
      setMessage("Enter a note first.");
      return;
    }

    setIsParsing(true);
    setMessage("");
    setParsedData(null);

    try {
      const response = await fetch(apiUrl("/parse-note"), {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          raw_text: note,
          currency,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        setMessage(data.detail || "Parse failed");
        return;
      }

      if (Array.isArray((data as ParsedTransactionBatch).transactions)) {
        const normalizedTransactions = (data as ParsedTransactionBatch).transactions.map(
          (transaction) => normalizeParsedData(transaction)
        );

        const canAutoSaveAll = normalizedTransactions.every(
          (transaction) =>
            transaction.review_level === "none" &&
            transaction.recurring_action === "none" &&
            !transaction.requires_conversion_confirmation
        );

        if (!canAutoSaveAll) {
          setParsedData(normalizedTransactions[0] || null);
          setMessage(
            `Found ${normalizedTransactions.length} transactions. Please review the first one before saving.`
          );
          return;
        }

        let savedCount = 0;
        for (const transaction of normalizedTransactions) {
          const saved = await saveTransactionDirect(transaction);
          if (saved) savedCount += 1;
        }

        if (savedCount > 0) {
          setParsedData(null);
          setNote("");
          setMessage(
            savedCount === 1
              ? "1 transaction saved automatically."
              : `${savedCount} transactions saved automatically.`
          );
          if (userId) {
            fetchTransactions(userId);
          }
        }

        return;
      }

      const normalized = normalizeParsedData(data);

      if (normalized.review_level === "none") {
        const saved = await saveTransactionDirect(normalized);

        if (saved) {
          setParsedData(null);
          setNote("");
          setMessage("Transaction saved automatically.");
          if (userId) {
            fetchTransactions(userId);
          }
        }

        return;
      }

      setParsedData(normalized);
      setPendingCancellationMatches([]);

      if (normalized.review_level === "quick") {
        setMessage(
          normalized.recurring_action === "cancel"
            ? "Recurring cancellation found. Please confirm before stopping projections."
            : "Almost ready. Please confirm before saving."
        );
      } else {
        setMessage("Needs review. Please check the details before saving.");
      }
    } catch {
      setMessage("Could not connect to backend");
    } finally {
      setIsParsing(false);
    }
  };

  const saveTransaction = async () => {
    if (!parsedData || !userId || userId === "__pending__") {
      setMessage("Missing parsed data or user");
      return;
    }

    try {
      const response = await fetch(
        apiUrl("/transactions"),
        {
          method: "POST",
          headers: getAuthHeaders(),
          body: JSON.stringify({
            user_id: userId,

            raw_text: parsedData.raw_text,
            date: parsedData.date,
            amount: parsedData.amount,
            currency: parsedData.currency,
            original_amount: parsedData.original_amount,
            original_currency: parsedData.original_currency,
            converted_amount: parsedData.converted_amount,
            converted_currency: parsedData.converted_currency,
            exchange_rate: parsedData.exchange_rate,
            exchange_rate_date: parsedData.exchange_rate_date,
            exchange_rate_source: parsedData.exchange_rate_source,
            exchange_rate_fetched_at: parsedData.exchange_rate_fetched_at,
            requires_conversion_confirmation:
              parsedData.requires_conversion_confirmation,
            conversion_error: parsedData.conversion_error,

            sender: parsedData.sender,
            receiver: parsedData.receiver,
            counterparty: parsedData.counterparty,

            category: parsedData.category,

            transaction_direction:
              parsedData.transaction_direction,

            source: parsedData.source,
            origin_type: parsedData.origin_type,

            status: parsedData.status,

            is_recurring: parsedData.is_recurring,

            confidence_score:
              parsedData.confidence_score,

            transaction_subject:
              parsedData.transaction_subject,

            subject_quality:
              parsedData.subject_quality,

            missing_fields:
              parsedData.missing_fields,

            ambiguity_reasons:
              parsedData.ambiguity_reasons,

            review_level: parsedData.review_level,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        setMessage(data.detail || "Save failed");
        return;
      }

      setMessage("Transaction saved.");

      setParsedData(null);
      setNote("");

      fetchTransactions(userId);
    } catch {
      setMessage("Could not connect to backend");
    }
  };

  const updateField = (
    field: keyof ParsedTransaction,
    value: string | number | boolean
  ) => {
    if (!parsedData) return;

    setParsedData({
      ...parsedData,
      [field]: value,
    });
  };

  const isMoneyOut = (transaction: Transaction) => {
    return ["expense", "loan_given", "gift_sent"].includes(
      transaction.transaction_direction
    );
  };

  const formatTransactionAmount = (transaction: Transaction) => {
    const sign = isMoneyOut(transaction) ? "-" : "+";
    return `${sign}${transaction.amount.toFixed(2)} ${transaction.currency}`;
  };

  const getWeekFromDate = (dateString: string) => {
    const { day } = getDateParts(dateString);

    if (day <= 7) return 1;
    if (day <= 14) return 2;
    if (day <= 21) return 3;
    if (day <= 28) return 4;
    return 5;
  };

  const openTransactionInReport = (transaction: Transaction) => {
    const { year, month } = getDateParts(transaction.date);
    const week = getWeekFromDate(transaction.date);

    router.push(
      `/report?year=${year}&month=${month}&week=${week}&transactionId=${transaction.id}`
    );
  };

  return (
    <>
      <Navbar />

      <style jsx global>{`
  @keyframes dotPulse {
    0%, 80%, 100% {
      transform: translateY(0);
      opacity: 0.45;
    }
    40% {
      transform: translateY(-4px);
      opacity: 1;
    }
  }

  @keyframes shimmerSweep {
    0% {
      left: -120%;
    }
    100% {
      left: 140%;
    }
  }
`}</style>

      {showWelcome && (
        <div
          style={{
            position: "fixed",
            top: animateWelcome ? "18px" : "90px",
            right: animateWelcome ? "24px" : "80px",
            opacity: animateWelcome ? 0 : 1,
            transform: animateWelcome ? "scale(0.75)" : "scale(1)",
            transition: "all 1.6s ease",
            background: "#ffffff",
            border: "1px solid #dbe4dc",
            borderRadius: "14px",
            padding: "0.85rem 1rem",
            boxShadow: "0 12px 30px rgba(30, 70, 45, 0.12)",
            zIndex: 2000,
            fontWeight: 700,
            color: "#17351f",
          }}
        >
          Hello {firstName}
        </div>
      )}

      <main style={pageStyle}>
        <section style={heroStyle}>
          <p style={eyebrowStyle}>Dashboard</p>
          <h1 style={titleStyle}>
            {firstName ? `Welcome, ${firstName}` : "Welcome"}
          </h1>
          <p style={subtitleStyle}>
            Your money workspace — capture, plan, and understand your finances in one place.
          </p>
        </section>

        <section style={journalCardStyle}>
          <div style={cardHeaderStyle}>
            <div>
              <h2 style={cardTitleStyle}>Nilebook Journal</h2>
              <p style={cardSubtitleStyle}>Describe a transaction</p>
            </div>

            <div style={currencyBadgeStyle}>{currency}</div>
          </div>

          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder={`Example: Lent 50 ${currency} to Joey Tribbiani yesterday using cash`}
            style={textareaStyle}
          />
      <div style={actionRowStyle}>
          <div style={{
                position: "relative",
                display: "inline-block",
                borderRadius: "999px",
                overflow: "hidden",
          }}
          onMouseEnter={() => setIsParseHovered(true)}
          onMouseLeave={() => setIsParseHovered(false)}
          >
            <button
                onClick={parseNote}
                disabled={isParsing}
                style={{
                  ...primaryButtonStyle,
                  opacity: isParsing ? 0.75 : 1,
                  cursor: isParsing ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  position: "relative",
                  zIndex: 2,
                  transform:
                    isParseHovered && !isParsing 
                    ? "translateY(-2px) scale(1.015)"
                    : "translateY(0px) scale(1)",
                  background:
                    isParseHovered && !isParsing ? "#249653" : "#1f7a45",
                  boxShadow:
                    isParseHovered && !isParsing
                      ? "0 16px 34px rgba(31, 122, 69, 0.32)"
                      : "0 10px 24px rgba(31, 122, 69, 0.22)",
                  transition: "all 0.22s cubic-bezier(0.4, 0, 0.2, 1)",
                }}
              >
                  {isParsing ? (
                    <>
                      Parsing <LoadingDots />
                    </>
                  ) : (
                    "Parse Note"
                  )}
              </button>

          {isParseHovered && !isParsing && (
            <span 
              style={{
                position: "absolute",
                top: 0,
                left: "-120%",
                width: "60%",
                height: "100%",
                background:
                  "linear-gradient(110deg, transparent 0%, rgba(255,255,255,0.42) 50%, transparent 100%)",
                transform: "skewX(-20deg)",
                animation: "shimmerSweep 1.1s ease forwards",
                zIndex: 3,
                pointerEvents: "none"
              }}
              />
            )}
            </div>

            <span style={hintStyle}>
              {isParsing
                ? "Please wait while your note is being understood."
                : "High-confidence notes save automatically."}
            </span>
          </div>

          {message && (
            <div style={messageStyle}>
              {message}
            </div>
          )}

          {parsedData && (
            <div style={resultWrapperStyle}>
              {parsedData.review_level === "quick" ? (
                <div style={quickCardStyle}>
                  <div style={quickHeaderStyle}>
                    <div>
                      <p style={eyebrowStyle}>Quick confirmation</p>
                      <h3 style={sectionTitleStyle}>
                        {parsedData.recurring_action === "cancel"
                          ? "Stop Recurring?"
                          : parsedData.requires_conversion_confirmation &&
                              parsedData.recurring_action === "create"
                            ? "Confirm Conversion & Recurring"
                          : parsedData.requires_conversion_confirmation
                            ? "Confirm Conversion"
                          : "Transaction Ready"}
                      </h3>
                    </div>

                    <span style={confidenceBadgeStyle}>
                      Confidence {Math.round(parsedData.confidence_score * 100)}%
                    </span>
                  </div>

                  <div style={summaryGridStyle}>
                    <SummaryItem label="Description" value={parsedData.raw_text} />
                    <SummaryItem
                      label="Amount"
                      value={`${parsedData.amount} ${parsedData.currency}`}
                    />
                    {hasConversion(parsedData) && (
                      <>
                        <SummaryItem
                          label="Original"
                          value={`${Number(parsedData.original_amount ?? 0).toFixed(
                            2
                          )} ${parsedData.original_currency}`}
                        />
                        <SummaryItem
                          label="Exchange Rate"
                          value={getConversionRateSummary(parsedData)}
                        />
                      </>
                    )}
                    <SummaryItem label="Category" value={parsedData.category} />
                    <SummaryItem label="From" value={parsedData.sender} />
                    <SummaryItem label="To" value={parsedData.receiver} />
                    <SummaryItem label="Source" value={parsedData.source} />
                    {parsedData.recurring_action === "create" && (
                      <SummaryItem
                        label="Recurring"
                        value={getRecurringTimeFrame(parsedData)}
                      />
                    )}
                  </div>

                  <div style={actionRowStyle}>
                    {parsedData.recurring_action === "create" ? (
                      <>
                        <button onClick={saveAsRecurring} style={primaryButtonStyle}>
                          Yes, Track Recurring
                        </button>

                        <button onClick={saveOnceOnly} style={secondaryButtonStyle}>
                          No, Save Once
                        </button>
                      </>
                    ) : parsedData.recurring_action === "cancel" ? (
                      <button onClick={cancelRecurringRule} style={primaryButtonStyle}>
                        Confirm Cancellation
                      </button>
                    ) : (
                      <button onClick={saveTransaction} style={primaryButtonStyle}>
                        Save Transaction
                      </button>
                    )}

                    <button
                      onClick={() =>
                        setParsedData({
                          ...parsedData,
                          review_level: "full",
                        })
                      }
                      style={secondaryButtonStyle}
                    >
                      Edit Details
                    </button>
                  </div>

                  {pendingCancellationMatches.length > 0 && (
                    <div style={matchListStyle}>
                      {pendingCancellationMatches.map((match) => (
                        <button
                          key={match.id}
                          onClick={() => confirmRecurringCancellationMatch(match.id)}
                          style={matchButtonStyle}
                        >
                          <span>
                            {match.name} • {match.amount.toFixed(2)}{" "}
                            {match.currency} • {match.frequency}
                          </span>
                          <span>{Math.round(match.score * 100)}%</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div style={reviewCardStyle}>
                  <div style={reviewHeaderStyle}>
                    <div>
                      <p style={eyebrowStyle}>Full review</p>
                      <h3 style={sectionTitleStyle}>Review Extracted Data</h3>
                    </div>

                    <span style={reviewBadgeStyle}>
                      Needs attention
                    </span>
                  </div>

                  <div style={formGridStyle}>
                    <Field label="Description">
                      <input
                        value={parsedData.raw_text}
                        onChange={(e) => updateField("raw_text", e.target.value)}
                        style={inputStyle}
                      />
                    </Field>

                    <Field label="Date">
                      <input
                        type="date"
                        value={parsedData.date}
                        onChange={(e) => updateField("date", e.target.value)}
                        style={inputStyle}
                      />
                    </Field>

                    <Field label="Amount">
                      <input
                        type="number"
                        step="0.01"
                        value={parsedData.amount}
                        onChange={(e) =>
                          updateField("amount", Number(e.target.value))
                        }
                        style={inputStyle}
                      />
                    </Field>

                    <Field label="Currency">
                      <input
                        value={parsedData.currency}
                        onChange={(e) => updateField("currency", e.target.value)}
                        style={inputStyle}
                      />
                    </Field>

                    {hasConversion(parsedData) && (
                      <>
                        <Field label="Original Amount">
                          <input
                            value={`${Number(parsedData.original_amount ?? 0).toFixed(
                              2
                            )} ${parsedData.original_currency}`}
                            readOnly
                            style={inputStyle}
                          />
                        </Field>

                        <Field label="Exchange Rate">
                          <input
                            value={getConversionRateSummary(parsedData)}
                            readOnly
                            style={inputStyle}
                          />
                        </Field>
                      </>
                    )}

                    <Field label="Sender">
                      <input
                        value={parsedData.sender}
                        onChange={(e) => updateField("sender", e.target.value)}
                        style={inputStyle}
                      />
                    </Field>

                    <Field label="Receiver">
                      <input
                        value={parsedData.receiver}
                        onChange={(e) => updateField("receiver", e.target.value)}
                        style={inputStyle}
                      />
                    </Field>

                    <Field label="Counterparty">
                      <input
                        value={parsedData.counterparty}
                        onChange={(e) =>
                          updateField("counterparty", e.target.value)
                        }
                        style={inputStyle}
                      />
                    </Field>

                    <Field label="Transaction Subject">
                      <input
                        value={parsedData.transaction_subject}
                        onChange={(e) =>
                          updateField("transaction_subject", e.target.value)
                        }
                        style={inputStyle}
                      />
                    </Field>

                    <Field label="Subject Quality">
                      <select
                        value={parsedData.subject_quality}
                        onChange={(e) =>
                          updateField(
                            "subject_quality",
                            e.target.value as
                              | "clear"
                              | "possibly_typo"
                              | "unclear"
                          )
                        }
                        style={inputStyle}
                      >
                        <option value="clear">clear</option>
                        <option value="possibly_typo">
                          possibly_typo
                        </option>
                        <option value="unclear">unclear</option>
                      </select>
                    </Field>

                    <Field label="Category">
                      <select
                        value={parsedData.category}
                        onChange={(e) => updateField("category", e.target.value)}
                        style={inputStyle}
                      >
                        {categories.map((c) => (
                          <option key={c} value={c}>
                            {c}
                          </option>
                        ))}
                      </select>
                    </Field>

                    <Field label="Direction">
                      <select
                        value={parsedData.transaction_direction}
                        onChange={(e) =>
                          updateField("transaction_direction", e.target.value)
                        }
                        style={inputStyle}
                      >
                        {directions.map((d) => (
                          <option key={d} value={d}>
                            {d}
                          </option>
                        ))}
                      </select>
                    </Field>

                    <Field label="Source">
                      <select
                        value={parsedData.source}
                        onChange={(e) => updateField("source", e.target.value)}
                        style={inputStyle}
                      >
                        {sources.map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                    </Field>

                    <Field label="Origin">
                      <input value={parsedData.origin_type} disabled style={disabledInputStyle} />
                    </Field>

                    <Field label="Status">
                      <input
                        value={parsedData.status}
                        onChange={(e) => updateField("status", e.target.value)}
                        style={inputStyle}
                      />
                    </Field>

                    <Field label="Review Level">
                      <select
                        value={parsedData.review_level}
                        onChange={(e) =>
                          updateField(
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

                    <Field label="Confidence Score">
                      <input
                        type="number"
                        step="0.01"
                        value={parsedData.confidence_score}
                        onChange={(e) =>
                          updateField(
                            "confidence_score",
                            Number(e.target.value)
                          )
                        }
                        style={inputStyle}
                      />
                    </Field>

                    <Field label="Missing Fields">
                      <input
                        value={parsedData.missing_fields.join(", ")}
                        disabled
                        style={disabledInputStyle}
                      />
                    </Field>

                    <Field label="Ambiguity Reasons">
                      <input
                        value={parsedData.ambiguity_reasons.join(", ")}
                        disabled
                        style={disabledInputStyle}
                      />
                    </Field>

                    <label style={checkboxLabelStyle}>
                      <input
                        type="checkbox"
                        checked={parsedData.is_recurring}
                        onChange={(e) =>
                          updateField("is_recurring", e.target.checked)
                        }
                      />
                      Recurring transaction
                    </label>

                    {(parsedData.is_recurring ||
                      parsedData.recurring_action === "create") && (
                      <div style={recurringTimeFrameStyle}>
                        {getRecurringTimeFrame(parsedData)}
                      </div>
                    )}
                  </div>

                  <div style={actionRowStyle}>
                    {parsedData.recurring_action === "create" ? (
                      <>
                        <button onClick={saveAsRecurring} style={primaryButtonStyle}>
                          Save And Track Recurring
                        </button>

                        <button onClick={saveOnceOnly} style={secondaryButtonStyle}>
                          Save Once
                        </button>
                      </>
                    ) : parsedData.recurring_action === "cancel" ? (
                      <button onClick={cancelRecurringRule} style={primaryButtonStyle}>
                        Confirm Cancellation
                      </button>
                    ) : (
                      <button onClick={saveTransaction} style={primaryButtonStyle}>
                        Save Transaction
                      </button>
                    )}

                    <button
                      onClick={() => {
                        setParsedData(null);
                        setPendingCancellationMatches([]);
                      }}
                      style={secondaryButtonStyle}
                    >
                      Cancel
                    </button>
                  </div>

                  {pendingCancellationMatches.length > 0 && (
                    <div style={matchListStyle}>
                      {pendingCancellationMatches.map((match) => (
                        <button
                          key={match.id}
                          onClick={() => confirmRecurringCancellationMatch(match.id)}
                          style={matchButtonStyle}
                        >
                          <span>
                            {match.name} • {match.amount.toFixed(2)}{" "}
                            {match.currency} • {match.frequency}
                          </span>
                          <span>{Math.round(match.score * 100)}%</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        <div style={historySectionStyle}>
          <div style={historyHeaderStyle}>
            <div>
                <p style={eyebrowStyle}>History</p>
                <h3 style={sectionTitleStyle}>Recent Transactions</h3>
            </div>
            <span style={historyCountStyle}>{transactions.length} shown</span>
          </div>

          {transactions.length === 0 ? (
            <p style={emptyHistoryStyle}>No transactions saved yet.</p>
          ) : (
            <div style={historyListStyle}>
              {transactions.map((transaction) => (
                <div
                  key={transaction.id}
                  style={historyItemStyle}
                  onClick={() => openTransactionInReport(transaction)}
                  title="Open in report"
                >
                  <div>
                    <strong style={historyDescriptionStyle}>
                      {transaction.raw_text}
                    </strong>
                    <p style={historyMetaStyle}>
                      {formatDateForCurrency(transaction.date, currency)} •{" "}
                      {transaction.category} • {transaction.source}
                      {hasConversion(transaction)
                        ? ` • ${getConversionSummary(transaction)}`
                        : ""}
                    </p>
                  </div>

                  <div
                    style={{
                      ...historyAmountStyle,
                      color: isMoneyOut(transaction) ? "#b42318" : "#1f7a45",
                    }}
                  >
                    {formatTransactionAmount(transaction)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        </section>
      </main>
    </>
  );
}

function SummaryItem({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={summaryItemStyle}>
      <span style={summaryLabelStyle}>{label}</span>
      <strong style={summaryValueStyle}>{value}</strong>
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

function LoadingDots() {
  return (
    <span style={dotsWrapperStyle}>
      <span style={{ ...dotStyle, animationDelay: "0s" }} />
      <span style={{ ...dotStyle, animationDelay: "0.15s" }} />
      <span style={{ ...dotStyle, animationDelay: "0.3s" }} />
    </span>
  );
}

const pageStyle: React.CSSProperties = {
  minHeight: "100vh",
  padding: "2rem",
  background: "linear-gradient(180deg, #f7fbf7 0%, #eef5ef 100%)",
  color: "#17351f",
};

const heroStyle: React.CSSProperties = {
  maxWidth: "980px",
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
  maxWidth: "680px",
  lineHeight: 1.6,
};

const journalCardStyle: React.CSSProperties = {
  width: "100%",
  maxWidth: "980px",
  margin: "0 auto",
  border: "1px solid #d8e7db",
  borderRadius: "22px",
  padding: "1.5rem",
  background: "rgba(255, 255, 255, 0.92)",
  boxShadow: "0 22px 60px rgba(35, 79, 48, 0.10)",
};

const cardHeaderStyle: React.CSSProperties = {
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

const currencyBadgeStyle: React.CSSProperties = {
  padding: "0.45rem 0.7rem",
  background: "#e8f4eb",
  border: "1px solid #cde2d1",
  color: "#1f5f35",
  borderRadius: "999px",
  fontWeight: 800,
  fontSize: "0.85rem",
};

const textareaStyle: React.CSSProperties = {
  width: "100%",
  minHeight: "130px",
  padding: "1rem",
  marginTop: "0.75rem",
  marginBottom: "1rem",
  border: "1px solid #cfded2",
  borderRadius: "16px",
  resize: "vertical",
  fontSize: "1rem",
  lineHeight: 1.5,
  outline: "none",
  background: "#fbfdfb",
  color: "#183921",
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

const hintStyle: React.CSSProperties = {
  color: "#6b7d70",
  fontSize: "0.9rem",
};

const messageStyle: React.CSSProperties = {
  marginTop: "1rem",
  padding: "0.8rem 1rem",
  background: "#f0f8f2",
  border: "1px solid #cfe6d5",
  borderRadius: "14px",
  color: "#225b34",
  fontWeight: 700,
};

const matchListStyle: React.CSSProperties = {
  marginTop: "1rem",
  display: "grid",
  gap: "0.65rem",
};

const matchButtonStyle: React.CSSProperties = {
  width: "100%",
  display: "flex",
  justifyContent: "space-between",
  gap: "1rem",
  padding: "0.85rem 1rem",
  borderRadius: "12px",
  border: "1px solid rgba(31, 122, 69, 0.22)",
  background: "#ffffff",
  color: "#173b28",
  cursor: "pointer",
  textAlign: "left",
};

const resultWrapperStyle: React.CSSProperties = {
  marginTop: "1.5rem",
};

const quickCardStyle: React.CSSProperties = {
  border: "1px solid #d7e7da",
  borderRadius: "18px",
  padding: "1.2rem",
  background: "#fbfdfb",
  maxWidth: "720px",
};

const quickHeaderStyle: React.CSSProperties = {
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

const confidenceBadgeStyle: React.CSSProperties = {
  padding: "0.45rem 0.65rem",
  borderRadius: "999px",
  background: "#eaf7ee",
  border: "1px solid #c8e8d2",
  color: "#1f6b3c",
  fontWeight: 800,
  fontSize: "0.82rem",
};

const summaryGridStyle: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
  gap: "0.75rem",
  marginBottom: "1rem",
};

const summaryItemStyle: React.CSSProperties = {
  padding: "0.8rem",
  border: "1px solid #e2ece4",
  borderRadius: "14px",
  background: "#ffffff",
};

const summaryLabelStyle: React.CSSProperties = {
  display: "block",
  color: "#6a7f70",
  fontSize: "0.78rem",
  marginBottom: "0.25rem",
  textTransform: "uppercase",
  letterSpacing: "0.04em",
  fontWeight: 700,
};

const summaryValueStyle: React.CSSProperties = {
  color: "#17351f",
  fontSize: "0.98rem",
  wordBreak: "break-word",
};

const reviewCardStyle: React.CSSProperties = {
  border: "1px solid #e5d8c6",
  borderRadius: "18px",
  padding: "1.2rem",
  background: "#fffdf9",
  maxWidth: "800px",
};

const reviewHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: "1rem",
  alignItems: "center",
  marginBottom: "1rem",
};

const reviewBadgeStyle: React.CSSProperties = {
  padding: "0.45rem 0.65rem",
  borderRadius: "999px",
  background: "#fff2df",
  border: "1px solid #f2d4a6",
  color: "#8a5a18",
  fontWeight: 800,
  fontSize: "0.82rem",
};

const formGridStyle: React.CSSProperties = {
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

const disabledInputStyle: React.CSSProperties = {
  ...inputStyle,
  background: "#eef3ef",
  color: "#6c7b70",
};

const checkboxLabelStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "0.5rem",
  fontWeight: 700,
  color: "#294c32",
  paddingTop: "1.6rem",
};

const recurringTimeFrameStyle: React.CSSProperties = {
  padding: "0.8rem",
  border: "1px solid #d8e7db",
  borderRadius: "14px",
  background: "#f7fbf7",
  color: "#225b34",
  fontWeight: 800,
};

const dotsWrapperStyle: React.CSSProperties = {
  display: "inline-flex",
  gap: "0.18rem",
  alignItems: "center",
};

const dotStyle: React.CSSProperties = {
  width: "5px",
  height: "5px",
  borderRadius: "50%",
  background: "#ffffff",
  display: "inline-block",
  animation: "dotPulse 0.9s infinite ease-in-out",
};

const historySectionStyle: React.CSSProperties = {
  marginTop: "1.5rem",
  paddingTop: "1.25rem",
  borderTop: "1px solid #e1ebe3",
};

const historyHeaderStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "1rem",
  marginBottom: "0.9rem",
};

const historyCountStyle: React.CSSProperties = {
  padding: "0.35rem 0.6rem",
  borderRadius: "999px",
  background: "#eef7f0",
  color: "#2a6b3f",
  fontWeight: 800,
  fontSize: "0.78rem",
};

const emptyHistoryStyle: React.CSSProperties = {
  margin: 0,
  color: "#6b7d70",
};

const historyListStyle: React.CSSProperties = {
  display: "grid",
  gap: "0.7rem",
};

const historyItemStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: "1rem",
  padding: "0.85rem",
  border: "1px solid #e2ece4",
  borderRadius: "14px",
  background: "#ffffff",
  cursor: "pointer",
  transition: "all 0.18s ease",
};

const historyDescriptionStyle: React.CSSProperties = {
  color: "#17351f",
  fontSize: "0.95rem",
};

const historyMetaStyle: React.CSSProperties = {
  margin: "0.25rem 0 0 0",
  color: "#6a7f70",
  fontSize: "0.82rem",
};

const historyAmountStyle: React.CSSProperties = {
  color: "#1f7a45",
  fontWeight: 900,
  whiteSpace: "nowrap",
};
