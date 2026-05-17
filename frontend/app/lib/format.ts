const currencyLocaleMap: Record<string, string> = {
  USD: "en-US",
  INR: "en-IN",
  EUR: "de-DE",
  GBP: "en-GB",
  CAD: "en-CA",
  AUD: "en-AU",
  JPY: "ja-JP",
  CNY: "zh-CN",
  RUB: "ru-RU",
  AED: "en-AE",
  CHF: "de-CH",
};

export function localeForCurrency(currency: string) {
  return currencyLocaleMap[String(currency || "").toUpperCase()] || "en-US";
}

export function formatDateForCurrency(dateString: string, currency: string) {
  const [year, month, day] = String(dateString || "").split("-").map(Number);

  if (!year || !month || !day) {
    return dateString;
  }

  return new Intl.DateTimeFormat(localeForCurrency(currency), {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(year, month - 1, day));
}
