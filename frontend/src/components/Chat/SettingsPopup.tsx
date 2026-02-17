import { useState } from "react";
import { useAuthStore } from "../../store/authStore";
import api from "../../api/client";

interface SettingsPopupProps {
  onClose: () => void;
}

export default function SettingsPopup({ onClose }: SettingsPopupProps) {
  const user = useAuthStore((s) => s.user);
  const fetchUser = useAuthStore((s) => s.fetchUser);

  const [username, setUsername] = useState(user?.username ?? "");
  const [safeWord, setSafeWord] = useState(user?.safe_word ?? "");
  const [exitWord, setExitWord] = useState(user?.exit_word ?? "");
  const [avatarStyle, setAvatarStyle] = useState(
    user?.avatar_config?.style ?? "photographic"
  );
  const [characterDescription, setCharacterDescription] = useState(
    user?.avatar_config?.character_description ?? ""
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSave = async () => {
    setSaving(true);
    setError("");
    try {
      await api.put("/auth/settings", {
        username: username.trim() || null,
        safe_word: safeWord,
        exit_word: exitWord,
        avatar_style: avatarStyle,
        character_description: characterDescription.trim() || null,
      });
      await fetchUser();
      onClose();
    } catch {
      setError("Failed to save settings. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md bg-gray-900 rounded-2xl p-6 space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-lg font-semibold text-white">Settings</h2>

        {/* Username */}
        <div>
          <label className="block text-sm text-gray-400 mb-1">Username</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          />
        </div>

        {/* Safe word */}
        <div>
          <label className="block text-sm text-gray-400 mb-1">
            Safe word <span className="text-gray-600">(enters Her mode)</span>
          </label>
          <input
            type="text"
            value={safeWord}
            onChange={(e) => setSafeWord(e.target.value)}
            placeholder="e.g. I am alone"
            className="w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          />
        </div>

        {/* Exit word */}
        <div>
          <label className="block text-sm text-gray-400 mb-1">
            Exit word <span className="text-gray-600">(leaves Her mode)</span>
          </label>
          <input
            type="text"
            value={exitWord}
            onChange={(e) => setExitWord(e.target.value)}
            placeholder="e.g. exit her"
            className="w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500"
          />
        </div>

        {/* Avatar style */}
        <div>
          <label className="block text-sm text-gray-400 mb-2">
            Avatar style
          </label>
          <div className="flex gap-3">
            {(["photographic", "manga", "artistic"] as const).map((style) => (
              <button
                key={style}
                onClick={() => setAvatarStyle(style)}
                className={`flex-1 py-2 rounded-lg text-sm capitalize transition-colors ${
                  avatarStyle === style
                    ? "bg-blue-600 text-white"
                    : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                }`}
              >
                {style}
              </button>
            ))}
          </div>
        </div>

        {/* Character description */}
        <div>
          <label className="block text-sm text-gray-400 mb-1">
            Character description
          </label>
          <textarea
            value={characterDescription}
            onChange={(e) => setCharacterDescription(e.target.value)}
            placeholder="Describe AVA's appearance..."
            rows={2}
            className="w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-white focus:outline-none focus:border-blue-500 resize-none"
          />
        </div>

        {error && <p className="text-red-400 text-sm">{error}</p>}

        {/* Buttons */}
        <div className="flex justify-end gap-3 pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm text-gray-400 hover:text-white bg-gray-800 hover:bg-gray-700 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 rounded-lg text-sm text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-50 transition-colors"
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
