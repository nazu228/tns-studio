//! Raw PDFium FFI and dynamic loader.
//!
//! The DLL is looked up in this order:
//! 1. `PDFIUM_DYNAMIC_LIB_PATH` (DLL path or directory),
//! 2. the directory containing the current executable,
//! 3. `CARGO_MANIFEST_DIR/vendor`.
//!
//! Load and symbol failures become [`PdfiumError`]; there is no fallback
//! parser. The library is initialised exactly once per process.

use libloading::Library;
use std::ffi::{c_char, c_double, c_float, c_int, c_ulong, c_void, CString};
use std::path::{Path, PathBuf};
use std::sync::OnceLock;

pub const VENDOR_PDFIUM_VERSION: &str = "153.0.7999.0";

pub type FpdfDocument = *mut c_void;
pub type FpdfPage = *mut c_void;
pub type FpdfTextPage = *mut c_void;
pub type FpdfPageObject = *mut c_void;
pub type FpdfPathSegment = *mut c_void;
pub type FpdfClipPath = *mut c_void;

const FPDF_PAGEOBJ_PATH: c_int = 2;
const FPDF_SEGMENT_LINETO: c_int = 0;

#[repr(C)]
struct LibraryVersion {
    major: c_int,
    minor: c_int,
    build: c_int,
    patch: c_int,
}

type FnInitLibrary = unsafe extern "system" fn();
type FnDestroyLibrary = unsafe extern "system" fn();
type FnGetVersion = unsafe extern "system" fn(*mut LibraryVersion);
type FnGetLastError = unsafe extern "system" fn() -> c_ulong;
type FnLoadDocument =
    unsafe extern "system" fn(*const c_char, *const c_char) -> FpdfDocument;
type FnCloseDocument = unsafe extern "system" fn(FpdfDocument);
type FnGetPageCount = unsafe extern "system" fn(FpdfDocument) -> c_int;
type FnGetPageWidthF = unsafe extern "system" fn(FpdfPage) -> c_float;
type FnGetPageHeightF = unsafe extern "system" fn(FpdfPage) -> c_float;
type FnGetMetaText = unsafe extern "system" fn(
    FpdfDocument,
    *const c_char,
    *mut c_void,
    c_ulong,
) -> c_ulong;
type FnLoadPage = unsafe extern "system" fn(FpdfDocument, c_int) -> FpdfPage;
type FnClosePage = unsafe extern "system" fn(FpdfPage);
type FnTextLoadPage = unsafe extern "system" fn(FpdfPage) -> FpdfTextPage;
type FnTextClosePage = unsafe extern "system" fn(FpdfTextPage);
type FnTextCountChars = unsafe extern "system" fn(FpdfTextPage) -> c_int;
type FnTextGetUnicode = unsafe extern "system" fn(FpdfTextPage, c_int) -> c_ulong;
type FnTextGetCharBox = unsafe extern "system" fn(
    FpdfTextPage,
    c_int,
    *mut c_double,
    *mut c_double,
    *mut c_double,
    *mut c_double,
) -> c_int;
type FnTextGetBoundedText = unsafe extern "system" fn(
    FpdfTextPage,
    c_double,
    c_double,
    c_double,
    c_double,
    *mut u16,
    c_int,
) -> c_int;
type FnPageCountObjects = unsafe extern "system" fn(FpdfPage) -> c_int;
type FnPageGetObject = unsafe extern "system" fn(FpdfPage, c_int) -> FpdfPageObject;
type FnPageObjGetType = unsafe extern "system" fn(FpdfPageObject) -> c_int;
type FnPageObjGetBounds = unsafe extern "system" fn(
    FpdfPageObject,
    *mut c_float,
    *mut c_float,
    *mut c_float,
    *mut c_float,
) -> c_int;
#[repr(C)]
#[derive(Clone, Copy, Default)]
struct FsMatrix {
    a: c_float,
    b: c_float,
    c: c_float,
    d: c_float,
    e: c_float,
    f: c_float,
}
type FnPageObjGetMatrix =
    unsafe extern "system" fn(FpdfPageObject, *mut FsMatrix) -> c_int;
type FnPathCountSegments = unsafe extern "system" fn(FpdfPageObject) -> c_int;
type FnPathGetPathSegment =
    unsafe extern "system" fn(FpdfPageObject, c_int) -> FpdfPathSegment;
type FnPathSegmentGetPoint =
    unsafe extern "system" fn(FpdfPathSegment, *mut c_float, *mut c_float) -> c_int;
type FnPathSegmentGetType = unsafe extern "system" fn(FpdfPathSegment) -> c_int;
type FnTextGetTextObject = unsafe extern "system" fn(FpdfTextPage, c_int) -> FpdfPageObject;
type FnPageObjGetClipPath = unsafe extern "system" fn(FpdfPageObject) -> FpdfClipPath;
type FnClipCountPaths = unsafe extern "system" fn(FpdfClipPath) -> c_int;
type FnClipCountSegments =
    unsafe extern "system" fn(FpdfClipPath, c_int) -> c_int;
type FnClipGetPathSegment =
    unsafe extern "system" fn(FpdfClipPath, c_int, c_int) -> FpdfPathSegment;

struct Api {
    _library: Library,
    #[allow(dead_code)]
    destroy_library: FnDestroyLibrary,
    get_version: Option<FnGetVersion>,
    get_last_error: FnGetLastError,
    load_document: FnLoadDocument,
    close_document: FnCloseDocument,
    get_page_count: FnGetPageCount,
    get_page_width: FnGetPageWidthF,
    get_page_height: FnGetPageHeightF,
    get_meta_text: FnGetMetaText,
    load_page: FnLoadPage,
    close_page: FnClosePage,
    text_load_page: FnTextLoadPage,
    text_close_page: FnTextClosePage,
    text_count_chars: FnTextCountChars,
    text_get_unicode: FnTextGetUnicode,
    text_get_char_box: FnTextGetCharBox,
    text_get_bounded_text: FnTextGetBoundedText,
    page_count_objects: FnPageCountObjects,
    page_get_object: FnPageGetObject,
    page_obj_get_type: FnPageObjGetType,
    page_obj_get_bounds: FnPageObjGetBounds,
    page_obj_get_matrix: FnPageObjGetMatrix,
    path_count_segments: FnPathCountSegments,
    path_get_path_segment: FnPathGetPathSegment,
    path_segment_get_point: FnPathSegmentGetPoint,
    path_segment_get_type: FnPathSegmentGetType,
    text_get_text_object: FnTextGetTextObject,
    page_obj_get_clip_path: FnPageObjGetClipPath,
    clip_count_paths: FnClipCountPaths,
    clip_count_segments: FnClipCountSegments,
    clip_get_path_segment: FnClipGetPathSegment,
}

unsafe impl Send for Api {}
unsafe impl Sync for Api {}

static API: OnceLock<Result<Api, PdfiumError>> = OnceLock::new();

/// Failure to load or initialise PDFium.
#[derive(Debug, Clone)]
pub struct PdfiumError {
    pub path: PathBuf,
    pub symbol: String,
    pub code: String,
}

impl std::fmt::Display for PdfiumError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "PDFium unavailable: path={} symbol={} code={}",
            self.path.display(),
            self.symbol,
            self.code
        )
    }
}

impl std::error::Error for PdfiumError {}

fn library_name() -> &'static str {
    if cfg!(windows) {
        "pdfium.dll"
    } else if cfg!(target_os = "macos") {
        "pdfium.dylib"
    } else {
        "libpdfium.so"
    }
}

fn candidates() -> Vec<PathBuf> {
    let mut paths = Vec::new();
    if let Some(value) = std::env::var_os("PDFIUM_DYNAMIC_LIB_PATH") {
        let path = PathBuf::from(value);
        if path.is_dir() {
            paths.push(path.join(library_name()));
        } else {
            paths.push(path);
        }
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(dir) = exe.parent() {
            paths.push(dir.join(library_name()));
        }
    }
    paths.push(
        PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("vendor")
            .join(library_name()),
    );
    paths
}

fn load() -> Result<Api, PdfiumError> {
    let mut last = PdfiumError {
        path: PathBuf::new(),
        symbol: "LoadLibrary".to_string(),
        code: "no candidate PDFium library found".to_string(),
    };
    for path in candidates() {
        let library = match unsafe { Library::new(&path) } {
            Ok(library) => library,
            Err(error) => {
                last = PdfiumError {
                    path,
                    symbol: "LoadLibrary".to_string(),
                    code: error.to_string(),
                };
                continue;
            }
        };
        match bind(library, &path) {
            Ok(api) => return Ok(api),
            Err(error) => last = error,
        }
    }
    Err(last)
}

unsafe fn symbol<T: Copy>(
    library: &Library,
    path: &Path,
    name: &str,
) -> Result<T, PdfiumError> {
    unsafe {
        library.get::<T>(name.as_bytes()).map(|s| *s).map_err(|error| PdfiumError {
            path: path.to_path_buf(),
            symbol: name.to_string(),
            code: error.to_string(),
        })
    }
}

fn bind(library: Library, path: &Path) -> Result<Api, PdfiumError> {
    unsafe {
        let init_library: FnInitLibrary = symbol(&library, path, "FPDF_InitLibrary")?;
        let api = Api {
            destroy_library: symbol(&library, path, "FPDF_DestroyLibrary")?,
            // PDFium 153 no longer exports this legacy symbol; keep it optional.
            get_version: library.get(b"FPDF_GetVersion").ok().map(|s| *s),
            get_last_error: symbol(&library, path, "FPDF_GetLastError")?,
            load_document: symbol(&library, path, "FPDF_LoadDocument")?,
            close_document: symbol(&library, path, "FPDF_CloseDocument")?,
            get_page_count: symbol(&library, path, "FPDF_GetPageCount")?,
            get_page_width: symbol(&library, path, "FPDF_GetPageWidthF")?,
            get_page_height: symbol(&library, path, "FPDF_GetPageHeightF")?,
            get_meta_text: symbol(&library, path, "FPDF_GetMetaText")?,
            load_page: symbol(&library, path, "FPDF_LoadPage")?,
            close_page: symbol(&library, path, "FPDF_ClosePage")?,
            text_load_page: symbol(&library, path, "FPDFText_LoadPage")?,
            text_close_page: symbol(&library, path, "FPDFText_ClosePage")?,
            text_count_chars: symbol(&library, path, "FPDFText_CountChars")?,
            text_get_unicode: symbol(&library, path, "FPDFText_GetUnicode")?,
            text_get_char_box: symbol(&library, path, "FPDFText_GetCharBox")?,
            text_get_bounded_text: symbol(&library, path, "FPDFText_GetBoundedText")?,
            page_count_objects: symbol(&library, path, "FPDFPage_CountObjects")?,
            page_get_object: symbol(&library, path, "FPDFPage_GetObject")?,
            page_obj_get_type: symbol(&library, path, "FPDFPageObj_GetType")?,
            page_obj_get_bounds: symbol(&library, path, "FPDFPageObj_GetBounds")?,
            page_obj_get_matrix: symbol(&library, path, "FPDFPageObj_GetMatrix")?,
            path_count_segments: symbol(&library, path, "FPDFPath_CountSegments")?,
            path_get_path_segment: symbol(&library, path, "FPDFPath_GetPathSegment")?,
            path_segment_get_point: symbol(&library, path, "FPDFPathSegment_GetPoint")?,
            path_segment_get_type: symbol(&library, path, "FPDFPathSegment_GetType")?,
            text_get_text_object: symbol(&library, path, "FPDFText_GetTextObject")?,
            page_obj_get_clip_path: symbol(&library, path, "FPDFPageObj_GetClipPath")?,
            clip_count_paths: symbol(&library, path, "FPDFClipPath_CountPaths")?,
            clip_count_segments: symbol(&library, path, "FPDFClipPath_CountPathSegments")?,
            clip_get_path_segment: symbol(&library, path, "FPDFClipPath_GetPathSegment")?,
            _library: library,
        };
        init_library();
        Ok(api)
    }
}

fn api() -> Result<&'static Api, PdfiumError> {
    API.get_or_init(load).as_ref().map_err(|error| error.clone())
}

/// Load the vendored/library PDFium and return its version.
pub fn version() -> Result<String, PdfiumError> {
    let api = api()?;
    if let Some(get_version) = api.get_version {
        let mut version = LibraryVersion {
            major: 0,
            minor: 0,
            build: 0,
            patch: 0,
        };
        unsafe { get_version(&mut version) };
        if version.major > 0 {
            return Ok(format!(
                "{}.{}.{}.{}",
                version.major, version.minor, version.build, version.patch
            ));
        }
    }
    Ok(VENDOR_PDFIUM_VERSION.to_string())
}

fn last_error(api: &Api) -> u32 {
    unsafe { (api.get_last_error)() as u32 }
}

fn last_error_name(code: u32) -> &'static str {
    match code {
        0 => "SUCCESS",
        1 => "UNKNOWN",
        2 => "FILE",
        3 => "FORMAT",
        4 => "PASSWORD",
        5 => "SECURITY",
        6 => "PAGE",
        _ => "OTHER",
    }
}

/// An opened PDF document. Pages borrow it so it cannot be closed early.
pub struct Document {
    api: &'static Api,
    raw: FpdfDocument,
}

impl Document {
    pub fn open(path: &Path) -> Result<Self, crate::PdfError> {
        let api = api().map_err(crate::PdfError::Pdfium)?;
        let path_string = path.to_str().ok_or_else(|| crate::PdfError::Open {
            path: path.to_path_buf(),
            code: "path is not valid UTF-8".to_string(),
        })?;
        let c_path = CString::new(path_string).map_err(|_| crate::PdfError::Open {
            path: path.to_path_buf(),
            code: "path contains NUL".to_string(),
        })?;
        let password = CString::new("").expect("empty CString");
        let raw = unsafe { (api.load_document)(c_path.as_ptr(), password.as_ptr()) };
        if raw.is_null() {
            let code = last_error(api);
            return Err(crate::PdfError::Open {
                path: path.to_path_buf(),
                code: format!("{} ({code})", last_error_name(code)),
            });
        }
        Ok(Self { api, raw })
    }

    pub fn page_count(&self) -> usize {
        let count = unsafe { (self.api.get_page_count)(self.raw) };
        count.max(0) as usize
    }

    pub fn meta(&self, tag: &str) -> Option<String> {
        let tag = CString::new(tag).ok()?;
        let length = unsafe {
            (self.api.get_meta_text)(self.raw, tag.as_ptr(), std::ptr::null_mut(), 0)
        } as usize;
        if length <= 2 {
            return None;
        }
        let mut buffer = vec![0u8; length];
        unsafe {
            (self.api.get_meta_text)(
                self.raw,
                tag.as_ptr(),
                buffer.as_mut_ptr().cast(),
                length as c_ulong,
            );
        }
        let text = decode_utf16_bytes(&buffer);
        if text.is_empty() {
            None
        } else {
            Some(text)
        }
    }

    pub fn page(&self, index: usize) -> Result<Page<'_>, crate::PdfError> {
        let raw = unsafe { (self.api.load_page)(self.raw, index as c_int) };
        if raw.is_null() {
            let code = last_error(self.api);
            return Err(crate::PdfError::Page {
                page: index + 1,
                message: format!("FPDF_LoadPage failed: {}", last_error_name(code)),
            });
        }
        Ok(Page {
            api: self.api,
            raw,
            _document: std::marker::PhantomData,
        })
    }
}

impl Drop for Document {
    fn drop(&mut self) {
        unsafe { (self.api.close_document)(self.raw) };
    }
}

pub struct Page<'a> {
    api: &'static Api,
    raw: FpdfPage,
    _document: std::marker::PhantomData<&'a Document>,
}

impl Page<'_> {
    pub fn width(&self) -> f64 {
        unsafe { (self.api.get_page_width)(self.raw) as f64 }
    }

    pub fn height(&self) -> f64 {
        unsafe { (self.api.get_page_height)(self.raw) as f64 }
    }

    pub fn text_page(&self) -> Result<TextPage<'_>, crate::PdfError> {
        let raw = unsafe { (self.api.text_load_page)(self.raw) };
        if raw.is_null() {
            let code = last_error(self.api);
            return Err(crate::PdfError::Parse {
                page: None,
                house: None,
                row: None,
                message: format!("FPDFText_LoadPage failed: {}", last_error_name(code)),
            });
        }
        Ok(TextPage {
            api: self.api,
            raw,
            _page: std::marker::PhantomData,
        })

    }

    pub fn paths(&self) -> Vec<PathObject> {
        let count = unsafe { (self.api.page_count_objects)(self.raw) }.max(0);
        let mut paths = Vec::new();
        for index in 0..count {
            let object = unsafe { (self.api.page_get_object)(self.raw, index) };
            if object.is_null()
                || unsafe { (self.api.page_obj_get_type)(object) } != FPDF_PAGEOBJ_PATH
            {
                continue;
            }
            let mut left = 0.0f32;
            let mut bottom = 0.0f32;
            let mut right = 0.0f32;
            let mut top = 0.0f32;
            let has_bounds = unsafe {
                (self.api.page_obj_get_bounds)(
                    object,
                    &mut left,
                    &mut bottom,
                    &mut right,
                    &mut top,
                )
            } != 0;
            let mut segments = Vec::new();
            let mut matrix = FsMatrix {
                a: 1.0,
                b: 0.0,
                c: 0.0,
                d: 1.0,
                e: 0.0,
                f: 0.0,
            };
            unsafe { (self.api.page_obj_get_matrix)(object, &mut matrix) };
            let segment_count = unsafe { (self.api.path_count_segments)(object) }.max(0);
            for segment_index in 0..segment_count {
                let segment =
                    unsafe { (self.api.path_get_path_segment)(object, segment_index) };
                if segment.is_null() {
                    continue;
                }
                let mut x = 0.0f32;
                let mut y = 0.0f32;
                if unsafe {
                    (self.api.path_segment_get_point)(segment, &mut x, &mut y)
                } == 0
                {
                    continue;
                }
                let local_x = x as f64;
                let local_y = y as f64;
                let x = matrix.a as f64 * local_x
                    + matrix.c as f64 * local_y
                    + matrix.e as f64;
                let y = matrix.b as f64 * local_x
                    + matrix.d as f64 * local_y
                    + matrix.f as f64;
                let kind = unsafe { (self.api.path_segment_get_type)(segment) };
                segments.push(Segment { kind, x, y });
            }
            if has_bounds {
                paths.push(PathObject {
                    bounds: Rect {
                        left: left as f64,
                        bottom: bottom as f64,
                        right: right as f64,
                        top: top as f64,
                    },
                    segments,
                });
            }
        }
        paths
    }
}

impl Drop for Page<'_> {
    fn drop(&mut self) {
        unsafe { (self.api.close_page)(self.raw) };
    }
}

pub struct TextPage<'a> {
    api: &'static Api,
    raw: FpdfTextPage,
    _page: std::marker::PhantomData<&'a ()>,
}

impl TextPage<'_> {
    pub fn count_chars(&self) -> usize {
        unsafe { (self.api.text_count_chars)(self.raw) }.max(0) as usize
    }

    /// Visible characters with their page-space boxes.
    ///
    /// PDFium's text page also exposes text that is clipped away by a text
    /// object's clip path. Those characters are not visible on the page and
    /// would otherwise leak into neighbouring table cells, so they are
    /// filtered here using the clip path bounding box.
    pub fn visible_chars(&self) -> Vec<VisibleChar> {
        let count = self.count_chars();
        let mut output = Vec::with_capacity(count);
        let mut index = 0;
        while index < count {
            let value = self.unicode(index);
            let (character, step) = if (0xD800..=0xDBFF).contains(&value) && index + 1 < count {
                let low = self.unicode(index + 1);
                if (0xDC00..=0xDFFF).contains(&low) {
                    let code = 0x10000 + ((value - 0xD800) << 10) + (low - 0xDC00);
                    (char::from_u32(code).unwrap_or('\u{FFFD}'), 2)
                } else {
                    (char::from_u32(value).unwrap_or('\u{FFFD}'), 1)
                }
            } else {
                (char::from_u32(value).unwrap_or('\u{FFFD}'), 1)
            };
            if character != '\0' {
                if let Some((left, right, bottom, top)) = self.char_box(index) {
                    let center_x = (left + right) / 2.0;
                    let center_y = (bottom + top) / 2.0;
                    if character.is_whitespace()
                        || self.char_is_visible(index, center_x, center_y)
                    {
                        output.push(VisibleChar {
                            character,
                            left,
                            right,
                            bottom,
                            top,
                        });
                    }
                }
            }
            index += step;
        }
        output
    }

    fn char_is_visible(&self, index: usize, center_x: f64, center_y: f64) -> bool {
        let object = unsafe { (self.api.text_get_text_object)(self.raw, index as c_int) };
        if object.is_null() {
            return true;
        }
        let clip = unsafe { (self.api.page_obj_get_clip_path)(object) };
        if clip.is_null() {
            return true;
        }
        let paths = unsafe { (self.api.clip_count_paths)(clip) };
        if paths <= 0 {
            return true;
        }
        for path in 0..paths {
            let segments = unsafe { (self.api.clip_count_segments)(clip, path) };
            if segments <= 0 {
                continue;
            }
            let mut left = f64::MAX;
            let mut right = f64::MIN;
            let mut bottom = f64::MAX;
            let mut top = f64::MIN;
            for segment_index in 0..segments {
                let segment =
                    unsafe { (self.api.clip_get_path_segment)(clip, path, segment_index) };
                if segment.is_null() {
                    continue;
                }
                let mut x = 0.0f32;
                let mut y = 0.0f32;
                if unsafe { (self.api.path_segment_get_point)(segment, &mut x, &mut y) } == 0 {
                    continue;
                }
                left = left.min(x as f64);
                right = right.max(x as f64);
                bottom = bottom.min(y as f64);
                top = top.max(y as f64);
            }
            if left <= right
                && center_x >= left - 0.5
                && center_x <= right + 0.5
                && center_y >= bottom - 0.5
                && center_y <= top + 0.5
            {
                return true;
            }
        }
        false
    }

    pub fn unicode(&self, index: usize) -> u32 {
        unsafe { (self.api.text_get_unicode)(self.raw, index as c_int) as u32 }
    }

    /// Character box in page space: left, right, bottom, top.
    pub fn char_box(&self, index: usize) -> Option<(f64, f64, f64, f64)> {
        let mut left = 0.0;
        let mut right = 0.0;
        let mut bottom = 0.0;
        let mut top = 0.0;
        let ok = unsafe {
            (self.api.text_get_char_box)(
                self.raw,
                index as c_int,
                &mut left,
                &mut right,
                &mut bottom,
                &mut top,
            )
        };
        (ok != 0).then_some((left, right, bottom, top))
    }

    /// Text whose characters fall into the rectangle. `top` is above `bottom`
    /// in PDF page space.
    pub fn bounded_text(&self, left: f64, top: f64, right: f64, bottom: f64) -> String {
        if right <= left || top <= bottom {
            return String::new();
        }
        let required = unsafe {
            (self.api.text_get_bounded_text)(
                self.raw,
                left,
                top,
                right,
                bottom,
                std::ptr::null_mut(),
                0,
            )
        };
        if required <= 0 {
            return String::new();
        }
        let mut buffer = vec![0u16; required as usize + 1];
        let mut written = unsafe {
            (self.api.text_get_bounded_text)(
                self.raw,
                left,
                top,
                right,
                bottom,
                buffer.as_mut_ptr(),
                buffer.len() as c_int,
            )
        };
        if written < 0 {
            return String::new();
        }
        if written as usize >= buffer.len() {
            buffer.resize(written as usize + 1, 0);
            written = unsafe {
                (self.api.text_get_bounded_text)(
                    self.raw,
                    left,
                    top,
                    right,
                    bottom,
                    buffer.as_mut_ptr(),
                    buffer.len() as c_int,
                )
            };
            if written < 0 {
                return String::new();
            }
        }
        decode_utf16(&buffer[..written as usize])
    }
}

impl Drop for TextPage<'_> {
    fn drop(&mut self) {
        unsafe { (self.api.text_close_page)(self.raw) };
    }
}

#[derive(Debug, Clone, Copy)]
pub struct Rect {
    pub left: f64,
    pub bottom: f64,
    pub right: f64,
    pub top: f64,
}

#[derive(Debug, Clone, Copy)]
pub struct VisibleChar {
    pub character: char,
    pub left: f64,
    pub right: f64,
    pub bottom: f64,
    pub top: f64,
}

#[derive(Debug, Clone, Copy)]
pub struct Segment {
    pub kind: c_int,
    pub x: f64,
    pub y: f64,
}

impl Segment {
    pub fn is_lineto(&self) -> bool {
        self.kind == FPDF_SEGMENT_LINETO
    }
}

#[derive(Debug, Clone)]
pub struct PathObject {
    pub bounds: Rect,
    pub segments: Vec<Segment>,
}

fn decode_utf16(units: &[u16]) -> String {
    let mut output = String::with_capacity(units.len());
    let mut index = 0;
    while index < units.len() {
        let unit = units[index];
        if (0xD800..=0xDBFF).contains(&unit) && index + 1 < units.len() {
            let low = units[index + 1];
            if (0xDC00..=0xDFFF).contains(&low) {
                let code = 0x10000
                    + (((unit as u32) - 0xD800) << 10)
                    + ((low as u32) - 0xDC00);
                output.push(char::from_u32(code).unwrap_or('\u{FFFD}'));
                index += 2;
                continue;
            }
        }
        output.push(char::from_u32(unit as u32).unwrap_or('\u{FFFD}'));
        index += 1;
    }
    output
}

fn decode_utf16_bytes(bytes: &[u8]) -> String {
    let mut units = Vec::with_capacity(bytes.len() / 2);
    let mut index = 0;
    while index + 1 < bytes.len() {
        let unit = u16::from_le_bytes([bytes[index], bytes[index + 1]]);
        if unit == 0 {
            break;
        }
        units.push(unit);
        index += 2;
    }
    decode_utf16(&units)
}

/// Decode a single PDFium text-page code unit (which may start a surrogate pair).
pub fn decode_char(text: &TextPage<'_>, index: usize) -> (char, usize) {
    let unit = text.unicode(index) as u16;
    if (0xD800..=0xDBFF).contains(&unit) && index + 1 < text.count_chars() {
        let low = text.unicode(index + 1) as u16;
        if (0xDC00..=0xDFFF).contains(&low) {
            let code =
                0x10000 + (((unit as u32) - 0xD800) << 10) + ((low as u32) - 0xDC00);
            return (char::from_u32(code).unwrap_or('\u{FFFD}'), 2);
        }
    }
    (char::from_u32(unit as u32).unwrap_or('\u{FFFD}'), 1)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn loads_vendored_pdfium() {
        let version = version().expect("PDFium must load from vendor");
        assert!(
            version.chars().next().is_some_and(|c| c.is_ascii_digit()),
            "unexpected version {version}"
        );
    }

    #[test]
    fn decodes_surrogate_pairs() {
        assert_eq!(decode_utf16(&[0xD83D, 0xDE00]), "😀");
        assert_eq!(decode_utf16(&[0x41, 0x42]), "AB");
    }
}
