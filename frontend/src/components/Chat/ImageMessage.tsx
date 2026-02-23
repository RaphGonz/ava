interface ImageMessageProps {
  images: string[];
}

export default function ImageMessage({ images }: ImageMessageProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {images.map((img, i) => (
        <img
          key={i}
          src={img}
          alt={`Generated image ${i + 1}`}
          className="rounded-lg max-w-sm max-h-96 object-contain"
        />
      ))}
    </div>
  );
}
