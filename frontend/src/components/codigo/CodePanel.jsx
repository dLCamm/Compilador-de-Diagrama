import { useEffect, useRef, useState } from "react";
import "./CodePanel.css";

function tokenizeCpp(line) {
  const cmtIdx = line.indexOf("//");
  if (cmtIdx !== -1) {
    return [
      ...tokenizeCppInner(line.slice(0, cmtIdx)),
      <span className="cmt" key="cmt">{line.slice(cmtIdx)}</span>,
    ];
  }
  return tokenizeCppInner(line);
}

function tokenizeCppInner(line) {
  const kwList = [
    "int","float","double","char","bool","void","if","else","while","for",
    "return","include","using","namespace","std","cout","cin","endl","string",
    "struct","class","public","private","const","true","false","NULL","nullptr",
    "main","printf","scanf",
  ];
  const tokens = line.split(/("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|\b\d+\.?\d*\b)/g);
  return tokens.map((tok, i) => {
    if (/^"/.test(tok) || /^'/.test(tok)) return <span className="str" key={i}>{tok}</span>;
    if (/^\d/.test(tok))                  return <span className="num" key={i}>{tok}</span>;
    return tok.split(/(\b\w+\b)/g).map((w, j) => {
      if (kwList.includes(w)) return <span className="kw"  key={`${i}-${j}`}>{w}</span>;
      if (/^#/.test(w))       return <span className="op"  key={`${i}-${j}`}>{w}</span>;
      return                         <span className="var" key={`${i}-${j}`}>{w}</span>;
    });
  });
}

function tokenizeAsm(line) {
  const trimmed = line.trimStart();
  if (trimmed.startsWith(";"))                   return <span className="asm-cmt">{line}</span>;
  if (/^section|^global|^extern/.test(trimmed)) return <span className="kw">{line}</span>;
  if (/^\w+:/.test(trimmed)) {
    const col = line.indexOf(":");
    return (
      <>
        <span className="lbl">{line.slice(0, col + 1)}</span>
        <span className="var">{line.slice(col + 1)}</span>
      </>
    );
  }
  const mnemonics = [
    "mov","add","sub","mul","div","cmp","jmp","je","jne","jl","jg","jle","jge",
    "call","ret","push","pop","lea","xor","and","or","not","inc","dec","nop",
    "int","imul","idiv","cdq","syscall","printf","section","global","extern",
    "db","dw","dd","resb","resw","resd",
  ];
  const parts = trimmed.split(/\s+/);
  if (mnemonics.includes(parts[0]?.toLowerCase())) {
    const indent     = line.slice(0, line.length - trimmed.length);
    const rest       = trimmed.slice(parts[0].length);
    const restTokens = rest.split(/(;.*$)/g);
    return (
      <>
        <span className="var">{indent}</span>
        <span className="asm-kw">{parts[0]}</span>
        {restTokens.map((t, i) =>
          t.startsWith(";")
            ? <span key={i} className="asm-cmt">{t}</span>
            : <span key={i} className="reg">{t}</span>
        )}
      </>
    );
  }
  return <span className="var">{line}</span>;
}

function normalizarEcho(echo, eventos, error) {
  const tieneErrorEnEcho = echo.some((paso) => paso.ok === false);

  const lineas = eventos.map((evento) => ({
    type: "info",
    prefix: "UI",
    text: [evento.stage, evento.mensaje].filter(Boolean).join(": "),
    time: evento.time ? new Date(evento.time) : new Date(),
    order: evento.order ?? 0,
  }));

  echo.forEach((paso) => {
    const type = paso.ok === false ? "error" : paso.ok === true ? "ok" : "info";
    const prefix = paso.ok === false ? "ERR" : paso.ok === true ? "OK" : "SYS";
    const mensaje = [paso.stage, paso.mensaje || paso.detalle]
      .filter(Boolean)
      .join(": ");

    lineas.push({
      type,
      prefix,
      text: mensaje,
      time: paso.time ? new Date(paso.time) : new Date(),
      order: paso.order ?? 0,
    });
  });

  if (error && !tieneErrorEnEcho) {
    lineas.push({
      type: "error",
      prefix: "ERR",
      text: error,
      time: new Date(),
      order: Number.MAX_SAFE_INTEGER,
    });
  }

  return lineas.sort((a, b) => {
    if (a.order !== b.order) return a.order - b.order;
    return a.time.getTime() - b.time.getTime();
  });
}

export default function CodePanel({
  codigoC = "",
  assembler = "",
  echo = [],
  eventos = [],
  status = "idle",
  error = "",
  onEchoEvent,
}) {
  const [activeTab,  setActiveTab]  = useState("cpp");
  const [copiado, setCopiado] = useState(false);
  const echoRef = useRef(null);

  useEffect(() => {
    if (echoRef.current) {
      echoRef.current.scrollTop = echoRef.current.scrollHeight;
    }
  }, [echo, eventos, error]);

  useEffect(() => {
    setCopiado(false);
  }, [activeTab, codigoC, assembler]);

  const cppCode = codigoC ? codigoC.split("\n") : [];
  const asmCode = assembler ? assembler.split("\n") : [];
  const echoLines = normalizarEcho(echo, eventos, error);
  const currentCode = activeTab === "cpp" ? cppCode : asmCode;
  const currentText = activeTab === "cpp" ? codigoC : assembler;
  const hasCode     = currentCode.length > 0;
  const hasEcho     = echoLines.length > 0;

  const copiarCodigo = async () => {
    if (!currentText) return;

    try {
      await navigator.clipboard.writeText(currentText);
      setCopiado(true);
      onEchoEvent?.(`Codigo ${activeTab === "cpp" ? "C" : "assembler"} copiado`);
      setTimeout(() => setCopiado(false), 1200);
    } catch (error) {
      console.error("No se pudo copiar el codigo.", error);
    }
  };

  return (
    <div className="code-panel">

      <div className="code-window">
        <div className="code-window-header">
          <div className="code-tabs">
            <button
              className={`tab-btn ${activeTab === "cpp" ? "active" : ""}`}
              onClick={() => setActiveTab("cpp")}
            >C</button>
            <button
              className={`tab-btn ${activeTab === "asm" ? "active" : ""}`}
              onClick={() => setActiveTab("asm")}
            >Assembler</button>
          </div>

          <button
            className={`copy-btn ${copiado ? "copied" : ""}`}
            onClick={copiarCodigo}
            disabled={!currentText}
            title="Copiar codigo"
          >
            {copiado ? "Copiado" : "Copiar"}
          </button>
        </div>

        <div className="code-body">
          {status === "idle" && (
            <div className="code-empty">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
              </svg>
              <span></span>
            </div>
          )}

          {status === "loading" && (
            <div className="code-empty">
              <div className="spinner" />
              <span>Conectando con el backend...</span>
            </div>
          )}

          {status === "error" && !hasCode && (
            <div className="code-empty">
              <span>{error || "No se pudo compilar el diagrama."}</span>
            </div>
          )}

          {status === "ready" && hasCode && (
            currentCode.map((line, i) => (
              <div className="line-row" key={i}>
                <span className="line-code">
                  {activeTab === "cpp" ? tokenizeCpp(line) : tokenizeAsm(line)}
                </span>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="echo-window">
        <div className="echo-header">
          <span className="echo-title">Echo</span>
        </div>

        <div className="echo-body" ref={echoRef}>
          {!hasEcho ? (
            <div className="echo-empty"></div>
          ) : (
            echoLines.map((l, i) => (
              <div className="echo-line" key={i}>
                <span className={`echo-prefix ${l.type}`}>{l.prefix}</span>
                <span className={`echo-text ${l.type}`}>{l.text}</span>
                <span className="echo-timestamp">
                  {l.time.toLocaleTimeString("es", {
                    hour: "2-digit", minute: "2-digit", second: "2-digit",
                  })}
                </span>
              </div>
            ))
          )}
          {status === "loading" && (
            <div className="echo-line">
              <span className="echo-prefix info">›</span>
              <span className="echo-text info"><span className="cursor-blink" /></span>
            </div>
          )}
        </div>
      </div>

    </div>
  );
}
