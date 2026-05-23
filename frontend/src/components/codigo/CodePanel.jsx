import { useState, useEffect, useRef } from "react";
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

const STATIC_CPP = [
  "#include <iostream>",
  "using namespace std;",
  "",
  "int main() {",
  "    int x;",
  "    cout << \"Ingresa x: \";",
  "    cin >> x;",
  "",
  "    if (x > 0) {",
  "        cout << \"x es positivo\" << endl;",
  "    } else {",
  "        cout << \"x no es positivo\" << endl;",
  "    }",
  "",
  "    return 0;",
  "}",
];

const STATIC_ASM = [
  "section .data",
  "    msg_pos  db \"x es positivo\", 10, 0",
  "    msg_neg  db \"x no es positivo\", 10, 0",
  "    fmt_in   db \"%d\", 0",
  "",
  "section .text",
  "    global main",
  "    extern printf, scanf",
  "",
  "main:",
  "    push    ebp",
  "    mov     ebp, esp",
  "    sub     esp, 4",
  "",
  "    lea     eax, [ebp-4]",
  "    push    eax",
  "    push    fmt_in",
  "    call    scanf",
  "    add     esp, 8",
  "",
  "    mov     eax, [ebp-4]",
  "    cmp     eax, 0",
  "    jle     .neg",
  "",
  ".pos:",
  "    push    msg_pos",
  "    call    printf",
  "    add     esp, 4",
  "    jmp     .end",
  "",
  ".neg:",
  "    push    msg_neg",
  "    call    printf",
  "    add     esp, 4",
  "",
  ".end:",
  "    mov     esp, ebp",
  "    pop     ebp",
  "    ret",
];

const STATIC_ECHO_STEPS = [
  { type: "info", prefix: "SYS", text: "Analizando nodos del diagrama...",       delay: 0   },
  { type: "step", prefix: "→",   text: "Nodo START detectado",                   delay: 350 },
  { type: "step", prefix: "→",   text: "Nodo PROCESO: lectura de variable x",    delay: 650 },
  { type: "step", prefix: "→",   text: "Nodo CONDICIÓN: x > 0",                 delay: 950 },
  { type: "step", prefix: "→",   text: "Rama TRUE  → imprimir positivo",         delay: 1200 },
  { type: "step", prefix: "→",   text: "Rama FALSE → imprimir no positivo",      delay: 1450 },
  { type: "step", prefix: "→",   text: "Nodo END alcanzado",                     delay: 1700 },
  { type: "ok",   prefix: "✓",   text: "Código C++ generado (17 líneas)",        delay: 2100 },
  { type: "ok",   prefix: "✓",   text: "Código ASM generado (42 líneas)",        delay: 2350 },
  { type: "ok",   prefix: "✓",   text: "Sin errores detectados",                 delay: 2600 },
];

export default function CodePanel({ onGenerate }) {
  const [activeTab,  setActiveTab]  = useState("cpp");
  const [status,     setStatus]     = useState("idle");
  const [cppCode,    setCppCode]    = useState([]);
  const [asmCode,    setAsmCode]    = useState([]);
  const [echoLines,  setEchoLines]  = useState([]);
  const echoRef = useRef(null);
  const timers  = useRef([]);

  useEffect(() => {
    if (echoRef.current) {
      echoRef.current.scrollTop = echoRef.current.scrollHeight;
    }
  }, [echoLines]);

  useEffect(() => () => timers.current.forEach(clearTimeout), []);

  const handleGenerate = () => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
    setStatus("loading");
    setCppCode([]);
    setAsmCode([]);
    setEchoLines([]);

    const t0 = setTimeout(() => {
      setCppCode(STATIC_CPP);
      setAsmCode(STATIC_ASM);
      setStatus("running");
    }, 400);
    timers.current.push(t0);

    STATIC_ECHO_STEPS.forEach(({ type, prefix, text, delay }) => {
      const t = setTimeout(() => {
        setEchoLines(prev => [
          ...prev,
          { type, prefix, text, time: new Date() },
        ]);
      }, 400 + delay);
      timers.current.push(t);
    });

    const lastDelay = STATIC_ECHO_STEPS.at(-1).delay;
    const tEnd = setTimeout(() => setStatus("ready"), 400 + lastDelay + 200);
    timers.current.push(tEnd);

    onGenerate?.();
  };

  useEffect(() => {
    window.__codePanelGenerate = handleGenerate;
    return () => { delete window.__codePanelGenerate; };
  }, [handleGenerate]);

  const currentCode = activeTab === "cpp" ? cppCode : asmCode;
  const hasCode     = currentCode.length > 0;
  const hasEcho     = echoLines.length > 0;

  return (
    <div className="code-panel">

      <div className="code-window">
        <div className="code-window-header">
          <button
            className={`tab-btn ${activeTab === "cpp" ? "active" : ""}`}
            onClick={() => setActiveTab("cpp")}
          >C++</button>
          <button
            className={`tab-btn ${activeTab === "asm" ? "active" : ""}`}
            onClick={() => setActiveTab("asm")}
          >Assembler</button>
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

          {(status === "running" || status === "ready") && hasCode && (
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
          {(status === "loading" || status === "running") && (
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