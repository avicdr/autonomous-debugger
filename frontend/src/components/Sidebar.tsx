import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { OutputTerminal } from "./OutputTerminal";
import { PatchesViewer } from "./PatchesViewer";

interface Patch {
  type: "add" | "remove" | "unchanged";
  line: number;
  content: string;
}

interface SidebarProps {
  output: string;
  status: "idle" | "success" | "error";
  responseTime?: number;
  patches: Patch[];
  onApplyPatch: () => void;
  onRevertPatch: () => void;
  isLoading?: boolean;
}

export const Sidebar = ({ 
  output, 
  status, 
  responseTime, 
  patches, 
  onApplyPatch, 
  onRevertPatch,
  isLoading 
}: SidebarProps) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div className={`h-full transition-all duration-300 ${isCollapsed ? "w-12" : "w-[450px]"} flex-shrink-0`}>
      {isCollapsed ? (
        <div className="h-full flex items-center justify-center bg-card border-l border-border">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsCollapsed(false)}
            className="rotate-180"
          >
            <ChevronRight className="w-5 h-5" />
          </Button>
        </div>
      ) : (
        <div className="h-full flex flex-col bg-gradient-to-b from-background to-muted/20 border-l border-border">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <h2 className="text-sm font-semibold">Debug Panel</h2>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsCollapsed(true)}
            >
              <ChevronRight className="w-5 h-5" />
            </Button>
          </div>
          <div className="flex-1 overflow-hidden">
            <Tabs defaultValue="output" className="h-full flex flex-col">
              <TabsList className="w-full justify-start rounded-none border-b border-border bg-transparent px-4">
                <TabsTrigger value="output" className="data-[state=active]:bg-muted rounded-md">
                  Output
                </TabsTrigger>
                <TabsTrigger value="patches" className="data-[state=active]:bg-muted rounded-md">
                  Patches
                  {patches.length > 0 && (
                    <span className="ml-2 px-1.5 py-0.5 text-xs bg-primary text-primary-foreground rounded-full">
                      {patches.length}
                    </span>
                  )}
                </TabsTrigger>
              </TabsList>
              <TabsContent value="output" className="flex-1 m-0 p-4">
                <OutputTerminal 
                  output={output} 
                  status={status} 
                  responseTime={responseTime}
                  isLoading={isLoading}
                />
              </TabsContent>
              <TabsContent value="patches" className="flex-1 m-0 p-4">
                <PatchesViewer
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
