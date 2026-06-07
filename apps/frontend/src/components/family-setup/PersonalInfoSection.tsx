import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FormField, FormItem, FormLabel, FormControl, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { User } from "lucide-react";
import { UseFormReturn } from "react-hook-form";

interface PersonalInfoSectionProps {
  form: UseFormReturn<any>;
}

export function PersonalInfoSection({ form }: PersonalInfoSectionProps) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Övrig information
          </CardTitle>
          <CardDescription>
            Fyll i extra information om er situation och behov
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <FormField
            control={form.control}
            name="personalDescription"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Personlig beskrivning</FormLabel>
                <FormControl>
                  <Textarea
                    placeholder="Berätta om er situation, era behov och vad ni hoppas få stöd med..."
                    className="min-h-[120px]"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="livingSituation"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Boendesituation</FormLabel>
                <FormControl>
                  <Input
                    placeholder="t.ex. Hyresrätt, bostadsrätt, med flera barn i hushållet..."
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="additionalNotes"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Övriga anteckningar</FormLabel>
                <FormControl>
                  <Textarea
                    placeholder="Eventuella övriga uppgifter som kan vara relevanta..."
                    className="min-h-[100px]"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </CardContent>
      </Card>
    </div>
  );
}