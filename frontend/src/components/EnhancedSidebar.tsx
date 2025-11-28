import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ChevronRight, Terminal, GitCompare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EnhancedOutputTerminal } from "./EnhancedOutputTerminal";
import { EnhancedPatchesViewer } from "./EnhancedPatchesViewer";

interface Patch {
  type: "add" | "remove" | "unchanged";
  line: number;
  content: string;
}

interface EnhancedSidebarProps {
  output: string;
  status: "idle" | "success" | "error";
  responseTime?: number;
  patches: Patch[];
  onApplyPatch: () => void;
  onRevertPatch: () => void;
  isLoading?: boolean;
  onClearOutput?: () => void;
  onRefreshOutput?: () => void;
}

export const EnhancedSidebar = ({
  output,
  status,
  responseTime,
  patches,
  onApplyPatch,
  onRevertPatch,
  isLoading,
  onClearOutput,
  onRefreshOutput,
}: EnhancedSidebarProps) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div
      className={`h-full transition-all duration-300 ${
        isCollapsed ? "w-14" : "w-[500px]"
      } flex-shrink-0`}
    >
      {isCollapsed ? (
        <div className="h-full flex items-center justify-center bg-card dark:bg-gradient-to-b dark:from-[#11151c] dark:to-[#0e1117] border-l border-border">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsCollapsed(false)}
            className="rotate-180 hover:scale-110 transition-transform"
          >
            <ChevronRight className="w-5 h-5" />
          </Button>
        </div>
      ) : (
        <div className="h-full flex flex-col bg-gradient-to-b from-background via-muted/10 to-background dark:from-[#0e1117] dark:via-[#11151c] dark:to-[#0e1117] border-l border-border">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border bg-card/50 dark:bg-card/20 backdrop-blur-sm">
            <h2 className="text-sm font-bold bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
              Debug Panel
            </h2>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsCollapsed(true)}
              className="hover:scale-110 transition-transform"
            >
              <ChevronRight className="w-5 h-5" />
            </Button>
          </div>

          <div className="flex-1 overflow-hidden">
            <Tabs defaultValue="output" className="h-full flex flex-col">
              <TabsList className="w-full justify-start rounded-none border-b border-border bg-transparent px-4 gap-2">
                <TabsTrigger
                  value="output"
                  className="data-[state=active]:bg-muted rounded-lg gap-2 transition-all data-[state=active]:shadow-sm"
                >
                  <Terminal className="w-3.5 h-3.5" />
                  <span className="font-medium">Output</span>
                </TabsTrigger>
                <TabsTrigger
                  value="patches"
                  className="data-[state=active]:bg-muted rounded-lg gap-2 transition-all data-[state=active]:shadow-sm relative"
                >
                  <GitCompare className="w-3.5 h-3.5" />
                  <span className="font-medium">Patches</span>
                  {patches.length > 0 && (
                    <span className="ml-1 px-2 py-0.5 text-xs bg-primary text-primary-foreground rounded-full font-semibold shadow-sm">
                      {patches.length}
                    </span>
                  )}
                </TabsTrigger>
              </TabsList>

              <TabsContent value="output" className="flex-1 m-0 p-4">
                <EnhancedOutputTerminal
                  output={output}
                  status={status}
                  responseTime={responseTime}
                  isLoading={isLoading}
                  onClear={onClearOutput}
                  onRefresh={onRefreshOutput}
                />
              </TabsContent>

              <TabsContent value="patches" className="flex-1 m-0 p-4">
                <EnhancedPatchesViewer
                  patches={patches}
                  onApplyPatch={onApplyPatch}
                  onRevertPatch={onRevertPatch}
                />
              </TabsContent>
            </Tabs>
          </div>
        </div>
      )}
    </div>
  );
};
