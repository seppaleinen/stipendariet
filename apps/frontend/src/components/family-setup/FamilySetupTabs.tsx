import { Tabs, TabsContent, TabsList, TabsTrigger } from "@stipendariet/ui";
import { Card } from "@stipendariet/ui";
import { Users, Heart, HelpCircle } from "lucide-react";
import { FamilyBasicInfo } from "./FamilyBasicInfo";
import { ChildNeeds } from "./ChildNeeds";
import { EconomySection } from "./EconomySection";

interface FamilySetupTabsProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
  form: any; // Use proper form type
}

export function FamilySetupTabs({ 
  currentTab, 
  setCurrentTab, 
  form 
}: FamilySetupTabsProps) {
  return (
    <Tabs
      value={currentTab}
      onValueChange={setCurrentTab}
      className="w-full"
    >
      <TabsList className="grid w-full grid-cols-3">
        <TabsTrigger value="basic" className="flex items-center gap-2">
          <Users className="h-4 w-4" />
          Basinformation
        </TabsTrigger>
        <TabsTrigger value="children" className="flex items-center gap-2">
          <Heart className="h-4 w-4" />
          Barnens behov
        </TabsTrigger>
        <TabsTrigger value="economy" className="flex items-center gap-2">
          <HelpCircle className="h-4 w-4" />
          Ekonomisk situation
        </TabsTrigger>
      </TabsList>

      <TabsContent value="basic">
        <Card className="p-6">
          <FamilyBasicInfo form={form} />
        </Card>
      </TabsContent>

      <TabsContent value="children">
        <Card className="p-6">
          <ChildNeeds form={form} />
        </Card>
      </TabsContent>

      <TabsContent value="economy">
        <Card className="p-6">
          <EconomySection form={form} />
        </Card>
      </TabsContent>
    </Tabs>
  );
}