import { useState } from "react";
import api from "../../api/client";
import { useAuthStore } from "../../store/authStore";

type Step = "age" | "username" | "preferences" | "safeword" | "style" | "confirm";

const STEPS: Step[] = ["age", "username", "preferences", "safeword", "style", "confirm"];

export default function OnboardingFlow() {
  const [stepIndex, setStepIndex] = useState(0);
  const [formData, setFormData] = useState({
    isAgeVerified: false,
    username: "",
    safeWord: "",
    avatarStyle: "photographic",
    orientation: "",
  });
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
    setError("");
    setStepIndex((i) => Math.min(i + 1, STEPS.length - 1));
  };
  const prev = () => {
    setError("");
    setStepIndex((i) => Math.max(i - 1, 0));
  };

  const submit = async () => {
    setLoading(true);
    setError("");
    try {
      await api.post("/onboarding/complete", {
        username: formData.username,
        is_age_verified: formData.isAgeVerified,
        safe_word: formData.safeWord || null,
        avatar_style: formData.avatarStyle,
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

        {step === "style" && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold">Avatar style</h2>
            <p className="text-gray-400 text-sm">
              Choose the visual style for AVA's generated images.
            </p>
            <div className="space-y-2">
              {[
                { value: "photographic", label: "Photographic", desc: "Realistic, high-quality photos" },
                { value: "manga", label: "Manga / Anime", desc: "Japanese animation style" },
                { value: "artistic", label: "Artistic", desc: "Stylized, painterly look" },
              ].map((opt) => (
                <label
                  key={opt.value}
                  className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-colors ${
                    formData.avatarStyle === opt.value
                      ? "bg-blue-900/40 ring-1 ring-blue-500"
                      : "bg-gray-800 hover:bg-gray-750"
                  }`}
                >
                  <input
                    type="radio"
                    name="style"
                    value={opt.value}
                    checked={formData.avatarStyle === opt.value}
                    onChange={(e) =>
                      setFormData({ ...formData, avatarStyle: e.target.value })
                    }
                    className="w-4 h-4"
                  />
                  <div>
                    <p className="text-sm font-medium">{opt.label}</p>
                    <p className="text-xs text-gray-500">{opt.desc}</p>
                  </div>
                </label>
              ))}
            </div>
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
              <p>
                <span className="text-gray-500">Style:</span> {formData.avatarStyle}
              </p>
              {formData.orientation && (
                <p>
                  <span className="text-gray-500">Orientation:</span>{" "}
                  {formData.orientation}
                </p>
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
