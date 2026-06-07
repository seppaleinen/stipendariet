import { useState } from "react";
import { Check, ChevronsUpDown, Plus, UserCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useProfile } from "@/contexts/ProfileContext";
import { useNavigate } from "react-router-dom";

export function ProfileSwitcher() {
  const { profiles, activeProfile, setActiveProfile, createProfile } = useProfile();
  const [open, setOpen] = useState(false);
  const [showNewProfileDialog, setShowNewProfileDialog] = useState(false);
  const [newProfileName, setNewProfileName] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const navigate = useNavigate();

  const handleCreateProfile = async () => {
    if (!newProfileName.trim()) return;
    
    setIsCreating(true);
    try {
      const newProfile = await createProfile({
        name: newProfileName,
      });
      setActiveProfile(newProfile);
      setShowNewProfileDialog(false);
      setNewProfileName("");
      // Navigate to setup for this new profile
      navigate("/profile-setup");
    } catch (error) {
      console.error("Failed to create profile:", error);
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-[200px] justify-between"
          >
            {activeProfile?.name ? (
              <div className="flex items-center gap-2 truncate">
                <UserCircle className="h-4 w-4 shrink-0 opacity-50" />
                <span className="truncate">{activeProfile.name}</span>
              </div>
            ) : (
              "Välj profil..."
            )}
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[200px] p-0">
          <Command>
            <CommandInput placeholder="Sök profil..." />
            <CommandList>
              <CommandEmpty>Ingen profil hittades.</CommandEmpty>
              <CommandGroup heading="Dina profiler">
                {profiles.map((profile) => (
                  <CommandItem
                    key={profile.id}
                    onSelect={() => {
                      setActiveProfile(profile);
                      setOpen(false);
                    }}
                    className="text-sm"
                  >
                    <Check
                      className={cn(
                        "mr-2 h-4 w-4",
                        activeProfile?.id === profile.id
                          ? "opacity-100"
                          : "opacity-0"
                      )}
                    />
                    {profile.name}
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
            <CommandSeparator />
            <CommandList>
              <CommandGroup>
                <CommandItem
                  onSelect={() => {
                    setOpen(false);
                    setShowNewProfileDialog(true);
                  }}
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Ny profil
                </CommandItem>
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>

      <Dialog open={showNewProfileDialog} onOpenChange={setShowNewProfileDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Skapa ny profil</DialogTitle>
            <DialogDescription>
              Lägg till en ny profil (t.ex. för en klient) för att hantera sökningar separat.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor="name" className="text-right">
                Namn
              </Label>
              <Input
                id="name"
                value={newProfileName}
                onChange={(e) => setNewProfileName(e.target.value)}
                placeholder="T.ex. Klient A"
                className="col-span-3"
                autoFocus
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleCreateProfile();
                }}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowNewProfileDialog(false)}
            >
              Avbryt
            </Button>
            <Button onClick={handleCreateProfile} disabled={isCreating}>
              {isCreating ? "Skapar..." : "Skapa profil"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
