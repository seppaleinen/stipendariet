import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@stipendariet/ui";
import { Separator } from "@stipendariet/ui";
import { FormField, FormItem, FormLabel, FormControl, FormMessage } from "@stipendariet/ui";
import { Input } from "@stipendariet/ui";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@stipendariet/ui";
import { Info } from "lucide-react";
import { UseFormReturn } from "react-hook-form";

interface FamilyBasicInfoProps {
  form: UseFormReturn<any>;
}

export function FamilyBasicInfo({ form }: FamilyBasicInfoProps) {
  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <FormField
          control={form.control}
          name="family.municipality"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Kommun / bostadsort *</FormLabel>
              <FormControl>
                <Input placeholder="t.ex. Stockholm" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="family.maritalStatus"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Civilstatus *</FormLabel>
              <Select
                onValueChange={field.onChange}
                defaultValue={field.value}
              >
                <FormControl>
                  <SelectTrigger>
                    <SelectValue placeholder="Välj civilstatus" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectItem value="married">Gift</SelectItem>
                  <SelectItem value="cohabiting">Sambo</SelectItem>
                  <SelectItem value="single">Ensamstående</SelectItem>
                  <SelectItem value="other">Annat</SelectItem>
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
        <FormField
          control={form.control}
          name="family.adults"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Antal vuxna i hushållet *</FormLabel>
              <FormControl>
                <Input
                  type="number"
                  min="1"
                  max="10"
                  {...field}
                  onChange={(e) =>
                    field.onChange(parseInt(e.target.value) || 0)
                  }
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="family.children"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Antal barn *</FormLabel>
              <FormControl>
                <Input
                  type="number"
                  min="0"
                  max="20"
                  {...field}
                  onChange={(e) =>
                    field.onChange(parseInt(e.target.value) || 0)
                  }
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
      </div>

      <Separator className="my-6" />

      {/* Detailed Family Members Section */}
      <div className="space-y-6">
        <h3 className="text-lg font-medium">Familjemedlemmar</h3>

        {/* Adults */}
        <div className="space-y-4">
          <h4 className="font-medium">Vuxna</h4>
          {Array.from({ length: form.watch("family.adults") || 1 }).map((_, index) => (
            <div key={`adult-${index}`} className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 border rounded-lg bg-gray-50">
              <FormField
                control={form.control}
                name={`adults.${index}.name`}
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Namn {index === 0 ? "(Primär)" : index + 1}</FormLabel>
                    <FormControl>
                      <Input
                        placeholder={`Namn på vuxen ${index + 1}`}
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name={`adults.${index}.age`}
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Ålder</FormLabel>
                    <FormControl>
                      <Input
                        type="number"
                        min="18"
                        max="100"
                        placeholder="ex. 35"
                        {...field}
                        onChange={(e) =>
                          field.onChange(parseInt(e.target.value) || 0)
                        }
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name={`adults.${index}.occupation`}
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Yrke</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="ex. Lärare, Sjuksköterska, etc."
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>
          ))}
        </div>

        {/* Children */}
        {form.watch("family.children") > 0 && (
          <div className="space-y-4">
            <h4 className="font-medium">Barn</h4>
            {Array.from({ length: form.watch("family.children") || 0 }).map((_, index) => (
              <div key={`child-${index}`} className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 border rounded-lg bg-blue-50">
                <FormField
                  control={form.control}
                  name={`childrenDetails.${index}.name`}
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Namn</FormLabel>
                      <FormControl>
                        <Input
                          placeholder={`Namn på barn ${index + 1}`}
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name={`childrenDetails.${index}.age`}
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Ålder</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min="0"
                          max="25"
                          placeholder="ex. 8"
                          {...field}
                          onChange={(e) =>
                            field.onChange(parseInt(e.target.value) || 0)
                          }
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name={`childrenDetails.${index}.needs`}
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Särskilda behov</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="ex. ADHD, Autism, etc."
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            ))}
          </div>
        )}
      </div>

      <Separator className="my-6" />

      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Info className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-lg font-medium">Kontaktuppgifter (valfritt)</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FormField
            control={form.control}
            name="family.email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>E-post</FormLabel>
                <FormControl>
                  <Input
                    placeholder="din.epost@example.com"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="family.phone"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Telefonnummer</FormLabel>
                <FormControl>
                  <Input
                    placeholder="+46 70 123 45 67"
                    {...field}
                  />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>
      </div>
    </>
  );
}