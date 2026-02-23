import { useState } from "react";
import api from "../../api/client";
import { useAuthStore } from "../../store/authStore";

type Step = "age" | "username" | "preferences" | "safeword" | "avatar" | "confirm";

const STEPS: Step[] = ["age", "username", "preferences", "safeword", "avatar", "confirm"];

export default function OnboardingFlow() {
  const [stepIndex, setStepIndex] = useState(0);
  const [formData, setFormData] = useState({
    isAgeVerified: false,
    username: "",
    safeWord: "",
    orientation: "",
    // Avatar fields
    gender: "woman",
    nation: "",
    description: "",
  });
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [comfyuiFilename, setComfyuiFilename] = useState<string>("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const fetchUser = useAuthStore((s) => s.fetchUser);

  const step = STEPS[stepIndex];

  const next = () => {
    if (step === "age" && !formData.isAgeVerified) {
      setError("You must confirm you are 18 or older.");
      return;
    }
    if (step === "username" && !formData.username.trim()) {
      setError("Please enter a name.");
      return;
    }
    if (step === "avatar" && !avatarUrl) {
      setError("Please generate and preview your avatar before continuing.");
      return;
    }
    setError("");
    setStepIndex((i) => Math.min(i + 1, STEPS.length - 1));
  };

  const prev = () => {
    setError("");
    setStepIndex((i) => Math.max(i - 1, 0));
  };

  const generateAvatar = async () => {
    if (!formData.nation.trim()) {
      setError("Please enter a nation or ethnicity.");
      return;
    }
    if (!formData.description.trim()) {
      setError("Please enter a description.");
      return;
    }
    setError("");
    setIsGenerating(true);
    try {
      const res = await api.post("/onboarding/generate-avatar", {
        gender: formData.gender,
        nation: formData.nation,
        description: formData.description,
      });
      setAvatarUrl(res.data.avatar_url + "?t=" + Date.now());
      setComfyuiFilename(res.data.comfyui_filename || "");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Avatar generation failed";
      setError(msg);
    } finally {
      setIsGenerating(false);
    }
  };

  const validateAndContinue = async () => {
    setError("");
    setLoading(true);
    try {
      await api.post("/onboarding/validate-avatar", {
        comfyui_filename: comfyuiFilename,
      });
      setStepIndex((i) => Math.min(i + 1, STEPS.length - 1));
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Validation failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const submit = async () => {
    setLoading(true);
    setError("");
    try {
      await api.post("/onboarding/complete", {
        username: formData.username,
        is_age_verified: formData.isAgeVerified,
        safe_word: formData.safeWord || null,
        preferences: formData.orientation ? { orientation: formData.orientation } : null,
      });
      await fetchUser();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Onboarding failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center h-screen">
      <div className="w-full max-w-md p-8 bg-gray-900 rounded-2xl">
        {/* Progress bar */}
        <div className="flex gap-1 mb-8">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-1 flex-1 rounded transition-colors ${
                i <= stepIndex ? "bg-blue-500" : "bg-gray-700"
              }`}
            />
          ))}
        </div>

        {step === "age" && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold">Welcome to AVA</h2>
            <p className="text-gray-400 text-sm">
              Before we get started, please confirm your age.
            </p>
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.isAgeVerified}
                onChange={(e) =>
                  setFormData({ ...formData, isAgeVerified: e.target.checked })
                }
                className="mt-1 w-4 h-4 rounded"
              />
              <span className="text-sm text-gray-300">
                I confirm that I am 18 years of age or older. I understand that this
                application may contain adult content.
              </span>
            </label>
          </div>
        )}

        {step === "username" && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold">What should AVA call you?</h2>
            <input
              type="text"
              value={formData.username}
              onChange={(e) =>
                setFormData({ ...formData, username: e.target.value })
              }
              placeholder="Your name"
              className="w-full rounded-xl bg-gray-800 px-4 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            />
          </div>
        )}

        {step === "preferences" && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold">Your preferences</h2>
            <p className="text-gray-400 text-sm">
              This helps AVA personalize the experience. Optional.
            </p>
            <select
              value={formData.orientation}
              onChange={(e) =>
                setFormData({ ...formData, orientation: e.target.value })
              }
              className="w-full rounded-xl bg-gray-800 px-4 py-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            >
              <option value="">Prefer not to say</option>
              <option value="hetero">Heterosexual</option>
              <option value="gay">Gay</option>
              <option value="bi">Bisexual</option>
              <option value="other">Other</option>
            </select>
          </div>
        )}

        {step === "safeword" && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold">Set a safe word</h2>
            <p className="text-gray-400 text-sm">
              Your safe word switches AVA between assistant mode (Jarvis) and intimate
              mode (Her). Type it in chat to toggle. Use a unique phrase.
            </p>
            <input
              type="text"
              value={formData.safeWord}
              onChange={(e) =>
                setFormData({ ...formData, safeWord: e.target.value })
              }
              placeholder="e.g. open sesame"
              className="w-full rounded-xl bg-gray-800 px-4 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            />
            <p className="text-gray-500 text-xs">Optional. You can set this later.</p>
          </div>
        )}

        {step === "avatar" && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold">Create your companion</h2>
            <p className="text-gray-400 text-sm">
              Describe your AI companion's appearance. A reference image will be generated
              for character consistency.
            </p>

            {/* Gender */}
            <div className="flex gap-2">
              {(["woman", "man"] as const).map((g) => (
                <button
                  key={g}
                  onClick={() => {
                    setFormData({ ...formData, gender: g });
                    setAvatarUrl(null);
                  }}
                  className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition-colors ${
                    formData.gender === g
                      ? "bg-blue-600 text-white"
                      : "bg-gray-800 text-gray-400 hover:bg-gray-750"
                  }`}
                >
                  {g.charAt(0).toUpperCase() + g.slice(1)}
                </button>
              ))}
            </div>

            {/* Nation / Ethnicity */}
            <input
              type="text"
              value={formData.nation}
              onChange={(e) => {
                setFormData({ ...formData, nation: e.target.value });
                setAvatarUrl(null);
              }}
              placeholder="Nation / ethnicity (e.g. African American, Japanese...)"
              className="w-full rounded-xl bg-gray-800 px-4 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            />

            {/* Description */}
            <textarea
              value={formData.description}
              onChange={(e) => {
                setFormData({ ...formData, description: e.target.value });
                setAvatarUrl(null);
              }}
              placeholder="Describe their appearance (hair color, eye color, body type, distinguishing features...)"
              rows={3}
              className="w-full rounded-xl bg-gray-800 px-4 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none"
            />

            {/* Generate button */}
            <button
              onClick={generateAvatar}
              disabled={isGenerating}
              className="w-full rounded-xl bg-purple-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-purple-500 disabled:opacity-40 transition-colors"
            >
              {isGenerating
                ? "Generating..."
                : avatarUrl
                ? "Regenerate"
                : "Generate Avatar"}
            </button>

            {/* Loading indicator */}
            {isGenerating && (
              <div className="flex items-center justify-center py-4">
                <div className="w-8 h-8 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
                <span className="ml-3 text-sm text-gray-400">
                  Creating your companion...
                </span>
              </div>
            )}

            {/* Preview */}
            {avatarUrl && !isGenerating && (
              <div className="flex flex-col items-center gap-3">
                <img
                  src={avatarUrl}
                  alt="Generated avatar"
                  className="rounded-xl max-h-64 object-contain border border-gray-700"
                />
                <p className="text-xs text-gray-500">
                  Not satisfied? Adjust the description and regenerate.
                </p>
              </div>
            )}
          </div>
        )}

        {step === "confirm" && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold">All set!</h2>
            <div className="space-y-2 text-sm text-gray-300">
              <p>
                <span className="text-gray-500">Name:</span> {formData.username}
              </p>
              <p>
                <span className="text-gray-500">Age verified:</span> Yes
              </p>
              <p>
                <span className="text-gray-500">Safe word:</span>{" "}
                {formData.safeWord || "Not set"}
              </p>
              {formData.orientation && (
                <p>
                  <span className="text-gray-500">Orientation:</span>{" "}
                  {formData.orientation}
                </p>
              )}
              {avatarUrl && (
                <div className="pt-2">
                  <span className="text-gray-500">Avatar:</span>
                  <img
                    src={avatarUrl}
                    alt="Your companion"
                    className="mt-2 rounded-xl max-h-40 object-contain border border-gray-700"
                  />
                </div>
              )}
            </div>
          </div>
        )}

        {error && <p className="text-red-400 text-sm mt-3">{error}</p>}

        <div className="flex justify-between mt-8">
          {stepIndex > 0 ? (
            <button
              onClick={prev}
              className="text-sm text-gray-400 hover:text-white transition-colors"
            >
              Back
            </button>
          ) : (
            <div />
          )}
          {step === "confirm" ? (
            <button
              onClick={submit}
              disabled={loading}
              className="rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-40 transition-colors"
            >
              {loading ? "Setting up..." : "Start Chatting"}
            </button>
          ) : step === "avatar" ? (
            <button
              onClick={validateAndContinue}
              disabled={!avatarUrl || isGenerating || loading}
              className="rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-40 transition-colors"
            >
              {loading ? "Validating..." : "Continue"}
            </button>
          ) : (
            <button
              onClick={next}
              className="rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-blue-500 transition-colors"
            >
              Continue
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
