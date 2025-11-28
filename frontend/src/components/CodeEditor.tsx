import Editor from "@monaco-editor/react";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";

interface CodeEditorProps {
  code: string;
  onChange: (value: string | undefined) => void;
  onFileUpload: (file: File) => void;
  theme: string;
}

export const CodeEditor = ({ code, onChange, onFileUpload, theme }: CodeEditorProps) => {
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.name.endsWith(".py")) {
      onFileUpload(file);
    }
  };

  return (
    <div className="h-full flex flex-col bg-card dark:bg-[#1a1d24] rounded-xl border border-border shadow-[var(--shadow-premium)] overflow-hidden">

      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r 
          from-muted/50 via-muted/30 to-muted/50 
          dark:from-[#171b22] dark:via-[#1a1f28] dark:to-[#171b22]
          border-b border-border backdrop-blur-sm">

        <div className="flex items-center gap-3">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-destructive/70" />
            <div className="w-3 h-3 rounded-full bg-warning/70" />
            <div className="w-3 h-3 rounded-full bg-success/70" />
          </div>
          <span className="text-sm font-semibold text-muted-foreground">main.py</span>
        </div>

        <label htmlFor="file-upload">
          <Button
            variant="outline"
            size="sm"
            className="gap-2 cursor-pointer hover:border-primary/50 transition-all"
            asChild
          >
            <span>
              <Upload className="w-4 h-4" />
              Upload .py
            </span>
          </Button>

          <input
            id="file-upload"
            type="file"
            accept=".py"
            onChange={handleFileChange}
            className="hidden"
          />
        </label>
      </div>

      {/* Monaco Editor */}
      <div className="flex-1 overflow-hidden relative">
        <Editor
          height="100%"
          language="python"
          value={code}
          onChange={onChange}
          theme={theme}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 4,
            wordWrap: "on",
            folding: true,
            padding: { top: 20, bottom: 16 },
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
            fontLigatures: true,
          }}
        />
      </div>
    </div>
  );
};
