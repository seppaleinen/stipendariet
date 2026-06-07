import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { FormField, FormItem, FormLabel, FormControl, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Heart, HelpCircle, Info } from "lucide-react";
import { UseFormReturn } from "react-hook-form";

interface ChildNeedsProps {
  form: UseFormReturn<any>;
}

export function ChildNeeds({ form }: ChildNeedsProps) {
  const childrenCount = form.watch("family.children") || 0;
  
  // Toggle diagnosis utility function
  const toggleDiagnosis = (childIndex: number, diagnosis: string) => {
    const currentChildren = form.getValues("children");
    const child = currentChildren[childIndex];
    const currentDiagnoses = child?.diagnoses || [];
    const updatedDiagnoses = currentDiagnoses.includes(diagnosis)
      ? currentDiagnoses.filter((d: string) => d !== diagnosis)
      : [...currentDiagnoses, diagnosis];
    
    form.setValue(`children.${childIndex}.diagnoses`, updatedDiagnoses);
  };

  return (
    <div className="space-y-6">
      {childrenCount === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <Heart className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>
            Inga barn tillagda. Ange antal barn i basinformation för
            att lägga till.
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {Array.from({ length: childrenCount }).map((_, index) => (
            <Card key={index} className="p-6 space-y-6 border-2 border-blue-100">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Heart className="h-5 w-5 text-red-500" />
                  <h4 className="text-lg font-medium">Barn {index + 1}</h4>
                </div>
                <Badge variant="secondary">Ålder: {form.watch(`children.${index}.age`) || "Ej ifylld"}</Badge>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name={`children.${index}.age`}
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Ålder *</FormLabel>
                      <FormControl>
                        <Input
                          type="number"
                          min="0"
                          max="25"
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
                  name={`children.${index}.needLevel`}
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Nivå av hjälpbehov *</FormLabel>
                      <Select
                        onValueChange={field.onChange}
                        defaultValue={field.value}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Välj hjälpbehov" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="0">
                            0 - lågt hjälpbehov
                          </SelectItem>
                          <SelectItem value="1">
                            1 - måttligt hjälpbehov
                          </SelectItem>
                          <SelectItem value="2">
                            2 - stort hjälpbehov
                          </SelectItem>
                          <SelectItem value="3">
                            3 - mycket stort hjälpbehov (t.ex. rullstolsburen,
                            omvårdnad dygnet runt)
                          </SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="space-y-4">
                <h5 className="font-medium flex items-center gap-2">
                  <HelpCircle className="h-4 w-4" />
                  Diagnoser (flera val möjliga)
                </h5>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* ADHD */}
                  <FormField
                    control={form.control}
                    name={`children.${index}.diagnoses`}
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={
                              field.value?.includes("adhd") || false
                            }
                            onCheckedChange={() => {
                              const currentValues = field.value || [];
                              const newValue = currentValues.includes("adhd")
                                ? currentValues.filter((v: string) => v !== "adhd")
                                : [...currentValues, "adhd"];
                              field.onChange(newValue);
                            }}
                          />
                        </FormControl>
                        <div className="space-y-1 leading-none">
                          <FormLabel>ADHD</FormLabel>
                        </div>
                      </FormItem>
                    )}
                  />

                  {/* Autism */}
                  <FormField
                    control={form.control}
                    name={`children.${index}.diagnoses`}
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={
                              field.value?.includes("autism") || false
                            }
                            onCheckedChange={() => {
                              const currentValues = field.value || [];
                              const newValue = currentValues.includes("autism")
                                ? currentValues.filter((v: string) => v !== "autism")
                                : [...currentValues, "autism"];
                              field.onChange(newValue);
                            }}
                          />
                        </FormControl>
                        <div className="space-y-1 leading-none">
                          <FormLabel>Autism / AST</FormLabel>
                        </div>
                      </FormItem>
                    )}
                  />

                  {/* Intellectual disability */}
                  <FormField
                    control={form.control}
                    name={`children.${index}.diagnoses`}
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={
                              field.value?.includes(
                                "intellectual_disability"
                              ) || false
                            }
                            onCheckedChange={() => {
                              const currentValues = field.value || [];
                              const newValue = currentValues.includes("intellectual_disability")
                                ? currentValues.filter((v: string) => v !== "intellectual_disability")
                                : [...currentValues, "intellectual_disability"];
                              field.onChange(newValue);
                            }}
                          />
                        </FormControl>
                        <div className="space-y-1 leading-none">
                          <FormLabel>
                            Intellektuell funktionsnedsättning
                          </FormLabel>
                        </div>
                      </FormItem>
                    )}
                  />

                  {/* CP */}
                  <FormField
                    control={form.control}
                    name={`children.${index}.diagnoses`}
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={
                              field.value?.includes("cp") || false
                            }
                            onCheckedChange={() => {
                              const currentValues = field.value || [];
                              const newValue = currentValues.includes("cp")
                                ? currentValues.filter((v: string) => v !== "cp")
                                : [...currentValues, "cp"];
                              field.onChange(newValue);
                            }}
                          />
                        </FormControl>
                        <div className="space-y-1 leading-none">
                          <FormLabel>CP / rörelsehinder</FormLabel>
                        </div>
                      </FormItem>
                    )}
                  />

                  {/* Acquired brain injury */}
                  <FormField
                    control={form.control}
                    name={`children.${index}.diagnoses`}
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={
                              field.value?.includes(
                                "acquired_brain_injury"
                              ) || false
                            }
                            onCheckedChange={() => {
                              const currentValues = field.value || [];
                              const newValue = currentValues.includes("acquired_brain_injury")
                                ? currentValues.filter((v: string) => v !== "acquired_brain_injury")
                                : [...currentValues, "acquired_brain_injury"];
                              field.onChange(newValue);
                            }}
                          />
                        </FormControl>
                        <div className="space-y-1 leading-none">
                          <FormLabel>Förvärvad hjärnskada</FormLabel>
                        </div>
                      </FormItem>
                    )}
                  />

                  {/* Other */}
                  <FormField
                    control={form.control}
                    name={`children.${index}.diagnoses`}
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={
                              field.value?.includes("other") || false
                            }
                            onCheckedChange={() => {
                              const currentValues = field.value || [];
                              const newValue = currentValues.includes("other")
                                ? currentValues.filter((v: string) => v !== "other")
                                : [...currentValues, "other"];
                              field.onChange(newValue);
                            }}
                          />
                        </FormControl>
                        <div className="space-y-1 leading-none">
                          <FormLabel>Annan diagnos</FormLabel>
                        </div>
                      </FormItem>
                    )}
                  />
                </div>
              </div>

              {form
                .watch(`children.${index}.diagnoses`)
                ?.includes("other") && (
                <FormField
                  control={form.control}
                  name={`children.${index}.otherDiagnosis`}
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Vilken annan diagnos?</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="Beskriv annan diagnos..."
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              )}

              <div className="space-y-4">
                <h5 className="font-medium flex items-center gap-2">
                  <HelpCircle className="h-4 w-4" />
                  Rörlighet och hjälpmedel
                </h5>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <FormField
                    control={form.control}
                    name={`children.${index}.mobility.wheelchair`}
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                        <div className="space-y-1 leading-none">
                          <FormLabel>Rullstol</FormLabel>
                        </div>
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name={`children.${index}.mobility.stairs`}
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                        <div className="space-y-1 leading-none">
                          <FormLabel>Kan inte hantera trappor</FormLabel>
                        </div>
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name={`children.${index}.mobility.supervision`}
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                        <FormControl>
                          <Checkbox
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                        <div className="space-y-1 leading-none">
                          <FormLabel>Behöver tillsyn</FormLabel>
                        </div>
                      </FormItem>
                    )}
                  />
                </div>

                <FormField
                  control={form.control}
                  name={`children.${index}.mobility.assistiveDevices`}
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Vilka hjälpmedel behövs?</FormLabel>
                      <FormControl>
                        <Input
                          placeholder="t.ex. rullator, gångstöd, etc..."
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}