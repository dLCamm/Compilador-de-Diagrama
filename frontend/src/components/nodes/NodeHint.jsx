import "./NodeHint.css";

export default function NodeHint({ titulo, lineas }) {
  return (
    <div className="node-hint">
      <div className="node-hint-title">{titulo}</div>
      {lineas.map((linea) => (
        <div className="node-hint-line" key={linea}>
          {linea}
        </div>
      ))}
    </div>
  );
}
