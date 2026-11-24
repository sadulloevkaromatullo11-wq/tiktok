export function compact(value) {
  const count = Number(value) || 0;
  if (count < 1000) return String(count);
  if (count < 1_000_000) {
    const text = (count / 1000).toFixed(count < 10000 ? 1 : 0).replace(".0", "");
    return `${text} ҳаз`;
  }
  return `${(count / 1_000_000).toFixed(1).replace(".0", "")} млн`;
}

export function ago(iso) {
  if (!iso) return "";
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 15) return "ҳозир";
  if (seconds < 60) return `${Math.floor(seconds)} сония`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} дақиқа`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} соат`;
  return `${Math.floor(seconds / 86400)} рӯз`;
}

export function initial(name) {
  return (name || "?").trim().charAt(0).toUpperCase();
}
