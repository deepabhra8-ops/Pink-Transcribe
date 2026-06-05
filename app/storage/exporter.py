import json
import math
from typing import List, Dict, Any, Optional

class TranscriptExporter:
    """Utility class to format and export transcript segments to various file formats."""

    @staticmethod
    def format_srt_timestamp(seconds: float) -> str:
        """Converts float seconds to SRT time format: HH:MM:SS,mmm"""
        if seconds < 0:
            seconds = 0.0
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int(round((seconds - math.floor(seconds)) * 1000))
        
        # Guard in case rounding makes milliseconds 1000
        if milliseconds >= 1000:
            milliseconds = 0
            secs += 1
            if secs >= 60:
                secs = 0
                minutes += 1
                if minutes >= 60:
                    minutes = 0
                    hours += 1
                    
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    @staticmethod
    def format_vtt_timestamp(seconds: float) -> str:
        """Converts float seconds to WebVTT time format: HH:MM:SS.mmm"""
        if seconds < 0:
            seconds = 0.0
        
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int(round((seconds - math.floor(seconds)) * 1000))
        
        # Guard in case rounding makes milliseconds 1000
        if milliseconds >= 1000:
            milliseconds = 0
            secs += 1
            if secs >= 60:
                secs = 0
                minutes += 1
                if minutes >= 60:
                    minutes = 0
                    hours += 1
                    
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"

    @classmethod
    def to_txt(
        cls, 
        segments: List[Dict[str, Any]], 
        include_speakers: bool = False, 
        include_timestamps: bool = False, 
        speaker_mapping: Optional[Dict[str, str]] = None
    ) -> str:
        """Joins segments into a formatted text block with optional speakers and timestamps."""
        lines = []
        for s in segments:
            text = s.get("text", "").strip()
            if not text:
                continue
            
            parts = []
            if include_timestamps:
                mins = int(s["start_time"] // 60)
                secs = int(s["start_time"] % 60)
                parts.append(f"[{mins:02d}:{secs:02d}]")
            
            if include_speakers:
                raw_spk = s.get("speaker", "Speaker 1")
                spk = speaker_mapping.get(raw_spk, raw_spk) if speaker_mapping else raw_spk
                parts.append(f"{spk}:")
                
            parts.append(text)
            lines.append(" ".join(parts))
            
        if include_speakers or include_timestamps:
            return "\n\n".join(lines)
        return " ".join(lines)

    @classmethod
    def to_json(
        cls, 
        session_metadata: Dict[str, Any], 
        segments: List[Dict[str, Any]],
        speaker_mapping: Optional[Dict[str, str]] = None
    ) -> str:
        """Wraps transcripts and metadata into a structured JSON string."""
        data = {
            "metadata": session_metadata,
            "segments": [
                {
                    "start_time": s["start_time"],
                    "end_time": s["end_time"],
                    "text": s["text"].strip(),
                    "confidence": s.get("confidence"),
                    "speaker": speaker_mapping.get(s.get("speaker", "Speaker 1"), s.get("speaker", "Speaker 1")) if speaker_mapping else s.get("speaker", "Speaker 1")
                }
                for s in segments
            ]
        }
        return json.dumps(data, indent=4, ensure_ascii=False)

    @classmethod
    def to_srt(
        cls, 
        segments: List[Dict[str, Any]], 
        include_speakers: bool = False, 
        speaker_mapping: Optional[Dict[str, str]] = None
    ) -> str:
        """Formats segments into SubRip (SRT) subtitle file format."""
        srt_lines = []
        index = 1
        for s in segments:
            text = s.get("text", "").strip()
            if not text:
                continue
            
            start_str = cls.format_srt_timestamp(s["start_time"])
            end_str = cls.format_srt_timestamp(s["end_time"])
            
            display_text = text
            if include_speakers:
                raw_spk = s.get("speaker", "Speaker 1")
                spk = speaker_mapping.get(raw_spk, raw_spk) if speaker_mapping else raw_spk
                display_text = f"[{spk}] {text}"
                
            srt_lines.append(str(index))
            srt_lines.append(f"{start_str} --> {end_str}")
            srt_lines.append(display_text)
            srt_lines.append("")  # Empty line separator
            index += 1
            
        return "\n".join(srt_lines)

    @classmethod
    def to_vtt(
        cls, 
        segments: List[Dict[str, Any]], 
        include_speakers: bool = False, 
        speaker_mapping: Optional[Dict[str, str]] = None
    ) -> str:
        """Formats segments into WebVTT (VTT) subtitle file format."""
        vtt_lines = ["WEBVTT", ""]
        for s in segments:
            text = s.get("text", "").strip()
            if not text:
                continue
            
            start_str = cls.format_vtt_timestamp(s["start_time"])
            end_str = cls.format_vtt_timestamp(s["end_time"])
            
            display_text = text
            if include_speakers:
                raw_spk = s.get("speaker", "Speaker 1")
                spk = speaker_mapping.get(raw_spk, raw_spk) if speaker_mapping else raw_spk
                display_text = f"<{spk}> {text}"
                
            vtt_lines.append(f"{start_str} --> {end_str}")
            vtt_lines.append(display_text)
            vtt_lines.append("")  # Empty line separator
            
        return "\n".join(vtt_lines)

    @classmethod
    def to_docx_html(
        cls, 
        segments: List[Dict[str, Any]], 
        speaker_mapping: Optional[Dict[str, str]] = None
    ) -> str:
        """Generates a beautifully formatted HTML transcript optimized for MS Word import."""
        html_lines = [
            "<html>",
            "<head>",
            "<meta charset='utf-8'>",
            "<style>",
            "body { font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.5; color: #111827; margin: 40px; }",
            "h1 { color: #ff6fa3; border-bottom: 2px solid #ff6fa3; padding-bottom: 8px; font-size: 24px; }",
            ".segment { margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #e5e7eb; }",
            ".timestamp { font-family: Consolas, monospace; color: #6b7280; font-size: 13px; font-weight: bold; }",
            ".speaker { font-weight: bold; color: #0f7a75; font-size: 14px; margin-left: 8px; }",
            ".text { margin-top: 4px; font-size: 15px; color: #111827; }",
            "</style>",
            "</head>",
            "<body>",
            "<h1>Transcript Document</h1>"
        ]
        
        for s in segments:
            text = s.get("text", "").strip()
            if not text:
                continue
            
            mins = int(s["start_time"] // 60)
            secs = int(s["start_time"] % 60)
            t_str = f"{mins:02d}:{secs:02d}"
            
            raw_spk = s.get("speaker", "Speaker 1")
            spk = speaker_mapping.get(raw_spk, raw_spk) if speaker_mapping else raw_spk
            
            html_lines.append("<div class='segment'>")
            html_lines.append(f"  <span class='timestamp'>[{t_str}]</span>")
            html_lines.append(f"  <span class='speaker'>{spk}</span>")
            html_lines.append(f"  <div class='text'>{text}</div>")
            html_lines.append("</div>")
            
        html_lines.append("</body>")
        html_lines.append("</html>")
        
        return "\n".join(html_lines)
