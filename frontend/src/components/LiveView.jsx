export default function LiveView({ onBack }) {
  return (
    <div className="page live-page">
      <div className="live-mark">LIVE</div>
      <h1 className="page-title">Пахши зинда</h1>
      <p className="hint">Ҳоло касе пахши зинда намекунад. Баъдтар ба ин ҷо бармегардед.</p>
      <button className="primary" onClick={onBack}>Ба тавсияҳо</button>
    </div>
  );
}
