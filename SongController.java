package prodo.marc.gosling.controllers;

import javafx.application.Platform;
import javafx.beans.property.ReadOnlyBooleanWrapper;
import javafx.beans.property.ReadOnlyObjectWrapper;
import javafx.collections.FXCollections;
import javafx.collections.ObservableList;
import javafx.collections.transformation.FilteredList;
import javafx.collections.transformation.SortedList;
import javafx.event.ActionEvent;
import javafx.fxml.FXML;
import javafx.scene.Scene;
import javafx.scene.control.Button;
import javafx.scene.control.Label;
import javafx.scene.control.TextField;
import javafx.scene.control.*;
import javafx.scene.control.cell.CheckBoxTableCell;
import javafx.scene.input.*;
import javafx.scene.media.Media;
import javafx.scene.media.MediaPlayer;
import javafx.util.Duration;
import org.apache.log4j.LogManager;
import org.apache.log4j.Logger;
import prodo.marc.gosling.dao.ID3Header;
import prodo.marc.gosling.dao.MyID3;
import prodo.marc.gosling.dao.Song;
import prodo.marc.gosling.hibernate.repository.SongRepository;
import prodo.marc.gosling.service.FileUtils;
import prodo.marc.gosling.service.MyStringUtils;
import prodo.marc.gosling.service.Popups;
import prodo.marc.gosling.service.SongGlobal;
import prodo.marc.gosling.service.id3.ID3Reader;
import prodo.marc.gosling.service.id3.ID3v2Utils;
import prodo.marc.gosling.service.util.TruncatedUtil;

import java.awt.*;
import java.io.File;
import java.io.IOException;
import java.math.RoundingMode;
import java.net.InetAddress;
import java.net.URI;
import java.net.UnknownHostException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.text.DecimalFormat;
import java.time.Year;
import java.util.List;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

public class SongController {

    private static final Logger logger = LogManager.getLogger(SongController.class);
    /**
     * Initial volume for mp3
     */
    private static final Integer INITIAL_VOLUME_SO_MY_EARS_DONT_EXPLODE = 40;

    @FXML
    ComboBox<String> dropGenre, doneFilter, truncatedFilter, userFilter;
    @FXML
    MediaPlayer mplayer;
    String filePlaying;
    @FXML
    Button songBackButton, addSongButton, addFolderButton, parseFilenameButton, googleSongButton,
            openLegacyDataButton, buttonUpdateSongs, buttonPlay, skipBack, skipForward, skipForwardSmall,
            skipBackSmall, buttonRevert, spotSongButton, zampSongButton, refreshTableButton, tableToggleButton,
            discogsSongButton, buttonNext, buttonCase, buttonExpandGenre;
    @FXML
    Label mp3Time, labelVolume, labelSongNumber, mp3Label;
    @FXML
    TableView<Song> songDatabaseTable;
    @FXML
    TableColumn<Song, String> tableArtist, tableTitle, tableAlbum, tablePublisher, tableComposer,
            tableGenre, tableISRC, tableFileLoc, tableEditor, tableDuration;
    @FXML
    TableColumn<Song, Integer> tableID;
    @FXML
    TableColumn<Song, Year> tableYear;
    @FXML
    TableColumn<Song, Boolean> tableDone;
    @FXML
    Slider mp3Slider, volumeSlider;
    @FXML
    CheckBox checkDone, checkCase;
    @FXML
    TextField textAlbum, textArtist, textTitle, textPublisher, textComposer, textYear, textISRC, textFilterFolder;

    //public text fiels for getting data from regex
    public static Button publicButtonRefresh;
    public static TextField publicTextArtist, publicTextTitle, publicTextPublisher, publicTextISRC, publicTextComposer;
    ObservableList<Song> songList = FXCollections.observableArrayList();
    ObservableList<String> publisherList = FXCollections.observableArrayList();
    FilteredList<Song> filteredSongs = new FilteredList<>(songList);
    SortedList<Song> sortedSongs = new SortedList<>(filteredSongs);
    String CHANGED_BACKGROUND_COLOR = "bb3333";
    String DEFAULT_BACKGROUND_COLOR = "555555";
    String AVERAGE_BACKGROUND_COLOR = "dd9999";
    private boolean UPDATE_CHECK = true;
    private boolean TIME_LEFT = false;
    private String EDITOR_NAME;
    //String NETWORK_FOLDER = "Z:\\";
    String NETWORK_FOLDER = "\\\\ONAIR\\B\\";

    /**
     * Loads the publisher list from the database
     */
    private void publisherAutocomplete() {
        //this neeeds to be a separate database eventually
        long timer = System.currentTimeMillis();
        List<String> publishers = SongRepository.getPublishers();
        logger.debug("publishers: " + publishers);
        logger.info("publishers loaded in " + (System.currentTimeMillis() - timer) + "ms");
        publisherList.addAll(publishers);
    }

    /**
     * Loads the list of genres, hard coded for now
     *
     * @return sorted list of genres
     */
    private String[] getGenres(String value) {
        String[] shortList = { "", "Cro", "Cro Zabavne", "Instrumental", "Kuruza", "Pop", "xxx", "Rock", "Country", "Dance"
        };
        String[] extraList = { "Klape", "Italian", "Susjedi", "Religiozne", "Oldies", "X-Mas", "Domoljubne",
                "World Music", "Slow", "Metal", "Navijacke", "Jazz", "Trance", "Electronic", "Acoustic", "Funk",
                "Club", "Blues", "Reggae",
        };
        String[] returnArr = shortList;
        //if input is + add extra genres to the list
        if (Objects.equals(value, "+")) {
            returnArr = new String[shortList.length + extraList.length];
            System.arraycopy(shortList, 0, returnArr, 0, shortList.length);
            System.arraycopy(extraList, 0, returnArr, shortList.length, extraList.length);
        }
        Arrays.sort(returnArr);
        return returnArr;
    }

    public void initialize() {

        logger.debug("----- Executing initialize");

        //declarations so regex can send data to song controller
        publicButtonRefresh = refreshTableButton;
        publicTextArtist = textArtist;
        publicTextTitle = textTitle;
        publicTextPublisher = textPublisher;
        publicTextISRC = textISRC;
        publicTextComposer = textComposer;

        //drag and drop
        songDatabaseTable.setOnDragOver(dragEvent -> {
            dragEvent.acceptTransferModes(TransferMode.LINK);
            dragEvent.consume();
        });
        songDatabaseTable.setOnDragDropped(dragEvent -> {
            testFiles(dragEvent);
            dragEvent.consume();
        });

        //double click table
        songDatabaseTable.setOnMousePressed(mouseEvent ->  {
                if (mouseEvent.isPrimaryButtonDown() && mouseEvent.getClickCount() == 2) {
                    playMP3();
                }
        });

        //getting editor name from system hostname
        try {
            EDITOR_NAME = InetAddress.getLocalHost().getHostName();
            logger.debug("Editor name: " + EDITOR_NAME);
        } catch (UnknownHostException ex) {
            logger.error("Unknown host:", ex);
        }

        //initializing dropdowns
        logger.debug("initializing dropdowns");
        expandGenre();
        dropGenre.setVisibleRowCount(13);
        doneFilter.getItems().addAll("Ignore done", "Done", "Not Done");
        truncatedFilter.getItems().addAll("Ignore truncated", "Truncated");
        userFilter.getItems().addAll("Any user", "Direktor", "Glazba", "ONAIR");

        //selecting items in dropdowns
        doneFilter.getSelectionModel().select(0);
        truncatedFilter.getSelectionModel().select(0);
        textFilterFolder.setText("");
        userFilter.getSelectionModel().select("Any user");

        //initializing table
        tableYear.setCellValueFactory(cellData -> new ReadOnlyObjectWrapper<>(cellData.getValue().getYear()));
        tableID.setCellValueFactory(cellData -> new ReadOnlyObjectWrapper<>(cellData.getValue().getId()));
        tableArtist.setCellValueFactory(cellData -> new ReadOnlyObjectWrapper<>(cellData.getValue().getArtist()));
        tableTitle.setCellValueFactory(cellData -> new ReadOnlyObjectWrapper<>(cellData.getValue().getTitle()));
        tableAlbum.setCellValueFactory(cellData -> new ReadOnlyObjectWrapper<>(cellData.getValue().getAlbum()));
        tablePublisher.setCellValueFactory(cellData -> new ReadOnlyObjectWrapper<>(cellData.getValue().getPublisher()));
        tableComposer.setCellValueFactory(cellData -> new ReadOnlyObjectWrapper<>(cellData.getValue().getComposer()));
        tableGenre.setCellValueFactory(cellData -> new ReadOnlyObjectWrapper<>(cellData.getValue().getGenre()));
        tableISRC.setCellValueFactory(cellData -> new ReadOnlyObjectWrapper<>(cellData.getValue().getISRC()));
        tableFileLoc.setCellValueFactory(cellData -> new ReadOnlyObjectWrapper<>(cellData.getValue().getFileLoc()));
        tableEditor.setCellValueFactory(cellData -> new ReadOnlyObjectWrapper<>(cellData.getValue().getEditor()));
        tableDuration.setCellValueFactory(cellData -> new ReadOnlyObjectWrapper<>(cellData.getValue().getDurationString()));

        tableDone.setCellValueFactory(cellData -> new ReadOnlyBooleanWrapper(cellData.getValue().getDone()));
        tableDone.setCellFactory(cellData -> new CheckBoxTableCell<>());

        //enable multiselect in table
        songDatabaseTable.getSelectionModel().setSelectionMode(SelectionMode.MULTIPLE);
        //handle selection change
        songDatabaseTable.getSelectionModel().selectedItemProperty().addListener((observable, oldValue, newValue) -> {
            if (newValue != null) {
                handleMultiSelectFields();
            }
        });

        //no clue
        sortedSongs.comparatorProperty().bind(songDatabaseTable.comparatorProperty());

        //setting voulume slider to initial value
        volumeSlider.setValue(INITIAL_VOLUME_SO_MY_EARS_DONT_EXPLODE);
        changeVolume();

        //loading songs and publishers from database
        updateTable();
        publisherAutocomplete();

        //load short table
        switchTable();

        //install accelerators
        Platform.runLater(this::installAccelerators);
        Platform.runLater(this::windowCloseListener);

        //if something is selected, load it into the text fields
        //this is mainy for when the window is reloaded
        if (!songDatabaseTable.getSelectionModel().isEmpty()) {
            updateTextFields(songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc());
        }

        //logger.debug("----- ending initialize");
    }

    /**
     * Installs Accelerators, so that the user can use the keyboard as conviniently as possible.
     * <p> Called on initialization.
     */
    public void installAccelerators() {
        Scene scene = buttonPlay.getScene();

        //shortcut ctrl+e to change case
        KeyCombination keyCombinationCase = new KeyCodeCombination(KeyCode.E, KeyCombination.SHORTCUT_DOWN);
        Runnable runCase = this::changeCase;
        scene.getAccelerators().put(keyCombinationCase, runCase);

        //shortcut ctrl+s to save
        KeyCombination keyCombinationSave = new KeyCodeCombination(KeyCode.S, KeyCombination.SHORTCUT_DOWN);
        Runnable runSave = this::updateMP3;
        scene.getAccelerators().put(keyCombinationSave, runSave);

        //shortcut F5 to update table
        KeyCombination keyCombinationUpdate = new KeyCodeCombination(KeyCode.F5);
        Runnable runUpdate = this::updateTable;
        scene.getAccelerators().put(keyCombinationUpdate, runUpdate);

        //shortcut ctrl+f to select the filter text field
        KeyCombination keyCombinationFind = new KeyCodeCombination(KeyCode.F, KeyCombination.SHORTCUT_DOWN);
        Runnable runFind = () -> textFilterFolder.requestFocus();
        scene.getAccelerators().put(keyCombinationFind, runFind);

        //shortcut ctrl+d to select done
        KeyCombination keyCombinationDone = new KeyCodeCombination(KeyCode.D, KeyCombination.SHORTCUT_DOWN);
        Runnable runDone = () -> checkDone.setSelected(!checkDone.isSelected());
        scene.getAccelerators().put(keyCombinationDone, runDone);

        //shortcut ctrl+down to select previous song in table
        KeyCombination keyCombinationPrevious = new KeyCodeCombination(KeyCode.UP, KeyCombination.SHORTCUT_DOWN);
        Runnable runPrevious = () -> {
            int temp = songDatabaseTable.getSelectionModel().getSelectedIndex()-1;
            if (temp == -1) temp = 0;
            songDatabaseTable.getSelectionModel().clearSelection();
            songDatabaseTable.getSelectionModel().select(temp);
            //songDatabaseTable.getSelectionModel().select(songDatabaseTable.getSelectionModel().getSelectedIndex() - 1);
            openMP3(songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc());
        };
        scene.getAccelerators().put(keyCombinationPrevious, runPrevious);

        //shortcut ctrl+up to select next song in table
        KeyCombination keyCombinationNext = new KeyCodeCombination(KeyCode.DOWN, KeyCombination.SHORTCUT_DOWN);
        Runnable runNext = () -> {
            int temp = songDatabaseTable.getSelectionModel().getSelectedIndex()+1;
            if (temp == songDatabaseTable.getItems().size()) temp = songDatabaseTable.getItems().size()-1;
            songDatabaseTable.getSelectionModel().clearSelection();
            songDatabaseTable.getSelectionModel().select(temp);            //songDatabaseTable.getSelectionModel().select(songDatabaseTable.getSelectionModel().getSelectedIndex() + 1);
            openMP3(songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc());
        };
        scene.getAccelerators().put(keyCombinationNext, runNext);

        //shortcut ctrl+page_down to select last song in table
        KeyCombination keyCombinationLast = new KeyCodeCombination(KeyCode.PAGE_DOWN, KeyCombination.SHORTCUT_DOWN);
        Runnable runLast = () -> {
            //songDatabaseTable.getSelectionModel().select(songList.size() - 1);
            songDatabaseTable.getSelectionModel().selectLast();
            songDatabaseTable.scrollTo(songList.size() - 1);
            openMP3(songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc());
        };
        scene.getAccelerators().put(keyCombinationLast, runLast);

        //shortcut ctrl+page_up to select first song in table
        KeyCombination keyCombinationFirst = new KeyCodeCombination(KeyCode.PAGE_UP, KeyCombination.SHORTCUT_DOWN);
        Runnable runFirts = () -> {
            //songDatabaseTable.getSelectionModel().select(0);
            songDatabaseTable.getSelectionModel().selectFirst();
            songDatabaseTable.scrollTo(0);
            openMP3(songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc());
        };
        scene.getAccelerators().put(keyCombinationFirst, runFirts);

        //shortcut ctrl+space to set filter text to "download" and update table
        KeyCombination keyCombinationDownload = new KeyCodeCombination(KeyCode.SPACE, KeyCombination.SHORTCUT_DOWN);
        Runnable runDownload = () -> {
            String filter = textFilterFolder.getText();
            if (filter.isEmpty()) {
                textFilterFolder.setText("download");
            } else {
                textFilterFolder.setText("");
            }
            updateTable();
        };
        scene.getAccelerators().put(keyCombinationDownload, runDownload);
    }

    /**
     * Listens for the window close event and asks the user if they want to save changes
     */
    public void windowCloseListener() {
        Scene scene = songDatabaseTable.getScene();
        scene.heightProperty().addListener((observable, oldValue, newValue) -> {
            double height = newValue.doubleValue();
            SongGlobal.setCurrentWindowHeight(height);
            logger.debug("window height changed to: " + height);
        });
    }


    @FXML
    protected void backToMain(ActionEvent event) throws IOException {
        //logger.debug("----- Executing backToMain");
        closeMediaStream();
        SceneController.openScene(event, "main", "view/hello-view.fxml", 300, 400);
        //logger.debug("----- ending backToMain");
    }

    @FXML
    protected void clickedParseButton() throws IOException {
        //logger.debug("----- Executing clickedParseButton");
        if (!songDatabaseTable.getSelectionModel().getSelectedItems().isEmpty()) {
            closeMediaStream();
            filePlaying = "";
            buttonPlay.setText("Play");
            List<Song> songs = new ArrayList<>(songDatabaseTable.getSelectionModel().getSelectedItems());
            SongGlobal.setSongList(songs);
            if (songs.isEmpty()) {
                Popups.giveInfoAlert("Open parse window error",
                        "Couldn't open the filename parse window",
                        "no file selected, file location=null");
            } else {
                SceneController.openWindow("view/parseFilename.fxml", true);
            }
        }
        //logger.debug("----- ending clickedParseButton");
    }

    @FXML
    protected void clickedFolderButton() {
        //logger.debug("----- Executing clickedFolderButton");
        Popups.giveInfoAlert("Info", "Opening folder: ", SongGlobal.getCurrentFolder());
        File pickedFolder = FileUtils.pickFolder(SongGlobal.getCurrentFolder());
        if (pickedFolder != null) {
            SongGlobal.setCurrentFolder(pickedFolder.toString());
            try {
                addSongsFromFolder(pickedFolder);
            } catch (IOException io) {
                Popups.giveInfoAlert("Error", "Could not open folder", pickedFolder.getAbsolutePath());
                logger.error("can't open folder", io);
            }
        }
        //logger.debug("----- ending clickedFolderButton");
    }

    @FXML
    protected void addSongsFromFolder(File directory) throws IOException {

        //logger.debug("----- Executing addSongsFromFolder");

        SongGlobal.setMP3List(FileUtils.getFileListFromFolder(directory, "mp3"));
        logger.debug("number of files in the list: " + SongGlobal.getMP3List().size());
        SongGlobal.setEditor(EDITOR_NAME);

        putMP3ListIntoDB();

        //logger.debug("----- ending addSongsFromFolder");
    }

    private void putMP3ListIntoDB() {

        String fxmlLocation = "/prodo/marc/gosling/view/progress.fxml";
        try {
            SceneController.openWindow(fxmlLocation, true);
            refreshTableButton.setStyle("-fx-background-color: #" + CHANGED_BACKGROUND_COLOR);
        } catch (IOException e) {
            logger.error("couldn't open import window", e);
        }

    }


    /**
     * Clear the table and get the new list of songs from the database
     */
    @FXML
    private void updateTable() {

        logger.debug("----- Executing updateTable");
        long timer = System.currentTimeMillis();

        SongRepository songRepo = new SongRepository();
        //long timer = System.currentTimeMillis();
        List<Song> songList1 = songRepo.getSongs();
        //logger.debug("time to get songs from database: " + (System.currentTimeMillis() - timer) + "ms");

        ArrayList<Integer> selectedSongList = getSelectedIDs();
        songList.clear();
        songList.addAll(songList1);
        filterTable();
        selectFileFromTable(selectedSongList);
        if (songDatabaseTable.getSelectionModel().getSelectedItems().size() == 1) {
            updateTextFields(songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc());
        }

        refreshTableButton.setStyle("");

        logger.debug("----- ending updateTable");
        logger.debug("updateTable took: " + (System.currentTimeMillis() - timer) + "ms");
    }

    private ArrayList<Integer> getSelectedIDs() {
        ArrayList<Integer> songList = new ArrayList<>();
        for (Song song : songDatabaseTable.getSelectionModel().getSelectedItems()) {
            songList.add(song.getId());
        }
        return songList;
    }


    @FXML
    public void clickTable(MouseEvent event) {

        //logger.debug("----- Executing clickTable");

        if (event.getButton() == MouseButton.SECONDARY) {
            logger.debug("right click");
            return; }

        if (event.getButton() == MouseButton.PRIMARY && songDatabaseTable.getSelectionModel().getSelectedItems().size() == 1) {
            try {
                openMP3(songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc());
            } catch (Exception e) {
                logger.error("no table entry clicked" + songDatabaseTable.getSelectionModel().getSelectedItem(), e);
            }
        } else {
            handleMultiSelectFields();
            checkFields();
        }
        songDatabaseTable.setMaxWidth(getTableWidth());

        //logger.debug("----- ending clickTable");
    }

    private void handleMultiSelectFields() {
        if (songDatabaseTable.getSelectionModel().getSelectedItems().size() > 1) {
            SongGlobal.setLastSongID(null);
            updateTextFields(songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc());
            //logger.debug("selected file: " + songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc());
            checkDone.setSelected(false);
            String diffetentText = "<?>";
            if (songDatabaseTable.getSelectionModel().getSelectedItems().isEmpty()) {
                textArtist.setText("");
                textTitle.setText("");
                textComposer.setText("");
                textAlbum.setText("");
                textYear.setText("");
                textPublisher.setText("");
                textISRC.setText("");
                dropGenre.getSelectionModel().select(0);
                mp3Label.setText("");
            } else {
                Song tempSong = songDatabaseTable.getSelectionModel().getSelectedItem();
                for (Song song : songDatabaseTable.getSelectionModel().getSelectedItems()) {
                    if (!song.getArtist().equals(tempSong.getArtist())) textArtist.setText(diffetentText);
                    if (!song.getTitle().equals(tempSong.getTitle())) textTitle.setText(diffetentText);
                    if (!song.getComposer().equals(tempSong.getComposer())) textComposer.setText(diffetentText);
                    if (!song.getAlbum().equals(tempSong.getAlbum())) textAlbum.setText(diffetentText);
                    if (textYear.getText() == null) textYear.setText("");
                    if (song.getYear() == null) song.setYear(Year.now());
                    if (!song.getYear().equals(tempSong.getYear())) textYear.setText(diffetentText);
                    if (!song.getPublisher().equals(tempSong.getPublisher())) textPublisher.setText(diffetentText);
                    if (!song.getISRC().equals(tempSong.getISRC())) textISRC.setText(diffetentText);
                    if (!song.getGenre().equals(tempSong.getGenre())) dropGenre.getSelectionModel().select(0);
                }
            }
        }
    }

    @FXML
    protected void openMP3(String fileLoc) {

        //logger.debug("----- Executing openMP3");
        if (songDatabaseTable.getSelectionModel().getSelectedItems().size() == 1) {

            Song currentSong = new Song();

            //TODO: this will need to change read mode to database... also needs to be at a different place
            boolean localFile;
            if (!EDITOR_NAME.equals(songDatabaseTable.getSelectionModel().getSelectedItem().getEditor()) &&
                    !songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc().contains(NETWORK_FOLDER)) {
                logger.debug("Error: file not local and editor is different!");
                localFile = false;
            } else {
                localFile = true;
            }


            if (!mp3Label.getText().isEmpty()) {
                currentSong.setArtist(textArtist.getText());
                currentSong.setTitle(textTitle.getText());
                currentSong.setAlbum(textAlbum.getText());
                currentSong.setPublisher(textPublisher.getText());
                currentSong.setComposer(textComposer.getText());
                currentSong.setYear(MyStringUtils.parseYear(textYear.getText()));
                currentSong.setGenre(dropGenre.getSelectionModel().getSelectedItem());
                currentSong.setISRC(textISRC.getText());
                currentSong.setFileLoc(SongGlobal.getLastSongID());
                currentSong.setDone(checkDone.isSelected());
                currentSong.setEditor(EDITOR_NAME);
            }


            String checkSong = currentSong.isTheSame(getSong(SongGlobal.getLastSongID()));
            logger.debug("last song: "+checkSong);
            logger.debug("curr song: "+currentSong.getFileLoc());
            logger.debug(songDatabaseTable.getSelectionModel().getSelectedItems().size());
            if (!checkSong.isEmpty() && currentSong.getFileLoc() != null && !checkSong.equals("one of the songs is empty") &&
                    !textYear.getText().equals("<?>") && !dropGenre.getSelectionModel().getSelectedItem().isEmpty()) {

                boolean result = Popups.giveConfirmAlert("Unsaved changes: " + songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc(),
                        "You are switching to another file with possible unsaved changes",
                        "Do you want to save the ID3 changes you have made?\n " + checkSong);

                if (result) {
                    updateMP3();
                } else {
                    ArrayList<Integer> selectedSongList = getSelectedIDs();
                    boolean resultNew = Popups.giveConfirmAlert("Continue?",
                            "do you still want to switch to another file?",
                            "Continue:");
                    if (!resultNew)
                        selectFileFromTable(selectedSongList);
                    else changeSong(fileLoc, localFile);
                }
            } else {
                changeSong(fileLoc, localFile);
            }

            //logger.debug("----- ending openMP3");
        }
    }

    private Song getSong(String lastSongID) {
        for (Song song : songDatabaseTable.getItems()) {
            if (song.getFileLoc().equals(lastSongID)) {
                return song;
            }
        }
        return null;
    }


    private void changeSong(String fileLoc, boolean localFile) {
        if (localFile) {
            updateTextFields(fileLoc);
            if (mplayer != null) {
                if (mplayer.getStatus() == MediaPlayer.Status.PLAYING) {
                    if (!Objects.equals(filePlaying, songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc())) {
                        buttonPlay.setText("Play");
                    } else {
                        buttonPlay.setText("Pause");
                    }
                }
            }
        }
    }


    private void updateTextFields(String fileLoc) {

        //logger.debug("----- Executing updateTextFields");

        //show file name
        String fileLabel = new File(fileLoc).getName();
        mp3Label.setText(fileLabel.replaceAll("(?i).mp3", ""));
        SongGlobal.setLastSongID(fileLoc);

        //load id3 data into text fields
        try {
            File file = new File(fileLoc);
            MyID3 id3Data = ID3Reader.getTag(file);


            textArtist.setText(id3Data.getData(ID3Header.ARTIST));
            textTitle.setText(id3Data.getData(ID3Header.TITLE));
            textAlbum.setText(id3Data.getData(ID3Header.ALBUM));
            textPublisher.setText(id3Data.getData(ID3Header.PUBLISHER));
            textComposer.setText(id3Data.getData(ID3Header.COMPOSER));
            if (id3Data.exists(ID3Header.YEAR)) {
                textYear.setText(id3Data.getData(ID3Header.YEAR));
            } else if (id3Data.exists(ID3Header.RECORDING_DATE)) {
                textYear.setText(id3Data.getData(ID3Header.RECORDING_DATE));
                id3Data.setFrame(ID3Header.YEAR, id3Data.getData(ID3Header.RECORDING_DATE));
            } else {
                textYear.setText(null);
            }
            if (id3Data.getData(ID3Header.KEY) != null) {
                checkDone.setSelected(id3Data.getData(ID3Header.KEY).equals("true"));
            } else {
                checkDone.setSelected(false);
            }
            //TODO: ovo ne bi trebalo radit vako... al genre ce ionako radit drugacije eventually...
            if (id3Data.getData(ID3Header.GENRE) != null) {
                dropGenre.getSelectionModel().select(MyStringUtils.replaceCroChars(id3Data.getData(ID3Header.GENRE), ID3Header.GENRE, true));
            }
            if (dropGenre.getSelectionModel().getSelectedItem() == null || id3Data.getData(ID3Header.GENRE) == null) {
                dropGenre.getSelectionModel().select(0);
            }
            if (dropGenre.getSelectionModel().getSelectedIndex() == -1) {
                logger.debug("could not find genre: " + id3Data.getData(ID3Header.GENRE));
            }
//            logger.debug("***" + id3Data.getData(ID3Header.GENRE) + "***");

            textISRC.setText(id3Data.getData(ID3Header.ISRC));

            String unknownFrames = id3Data.checkFrames().toString();
            if (!unknownFrames.equals("[]")) {
                Popups.giveInfoAlert("Unknown ID3 header in file: ", file.toString(), unknownFrames);
                //logger.debug(unknownFrames);
            }

            checkFields();

        } catch (Exception report) {
            logger.error("Error while opening file " + fileLoc, report);
        }

        //logger.debug("----- ending updateTextFields");
    }

    /**
     * This method selects the current songs from the table
     *
     * @param songIDList list of song IDs to be selected
     */
    private void selectFileFromTable(ArrayList<Integer> songIDList) {
        songDatabaseTable.getSelectionModel().clearSelection();
        //logger.debug("file list: " + songIDList.toString());
        for (int songID : songIDList) {
            for (Song song : songDatabaseTable.getItems()) {
                if (song.getId() == songID) {
                    songDatabaseTable.getSelectionModel().select(song);
                }
            }
        }
    }

    @FXML
    protected void playMP3() {
        //logger.debug("----- Executing playMP3");

        if (mplayer == null || !Objects.equals(filePlaying, songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc())) {
            openMediaFile(songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc());
        }

        if (mplayer == null && Objects.equals(buttonPlay.getText(), "Play")) {
            logger.debug("no file open to play");
            return;
        }

        filePlaying = songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc();
        logger.debug("STATUS: " + mplayer.getStatus());

        if (mplayer.getStatus() == MediaPlayer.Status.PLAYING) {
            buttonPlay.setText("Play");
            mplayer.pause();
            logger.debug("---PAUSE---");
            return;
        }

        if (mplayer.getStatus() == MediaPlayer.Status.PAUSED) {
            buttonPlay.setText("Pause");
            mplayer.play();
            logger.debug("---UN-PAUSE---");
            return;
        }

            //play file
            mplayer.setVolume(volumeSlider.getValue() / 100);
            buttonPlay.setText("Pause");
            mplayer.play();

            //timer for updating current position slider
            Timer sliderUpdateTimer = new Timer();
            TimerTask sliderUpdateTask = new TimerTask() {
                public void run() {
                    double totalTime = mplayer.getTotalDuration().toSeconds();
                    double currentTime = mplayer.getCurrentTime().toSeconds();
                    if (TIME_LEFT) currentTime = totalTime - currentTime;
                    int minutes = (int) Math.floor(currentTime / 60);
                    double seconds = currentTime - minutes * 60;
                    DecimalFormat df = new DecimalFormat("##.#");
                    df.setRoundingMode(RoundingMode.DOWN);
                    String secondsString = df.format(seconds);
                    if (!secondsString.contains(".")) {
                        secondsString += ".0";
                    }
                    if (seconds < 10) {
                        secondsString = "0" + secondsString;
                    }
                    String finalSecondsString = secondsString;
                    Platform.runLater(() -> {
                        //show current time text, needs improving
                        mp3Time.setText(String.format("%02dm ", minutes) + finalSecondsString + "s");
                        if (TIME_LEFT) {
                            mp3Time.setText("-" + mp3Time.getText());
                        } else {
                            mp3Time.setText(" " + mp3Time.getText());
                        }
                        //update slider to current time
                        if (UPDATE_CHECK) {
                            mp3Slider.setValue(mplayer.getCurrentTime().toMillis() / 100);
                        }
                    });
                }
            };
            sliderUpdateTimer.scheduleAtFixedRate(sliderUpdateTask, 100, 100);

        //logger.debug("----- ending playMP3");

    }

    @FXML
    protected void moveTime() {
        if (mplayer != null) {
            mplayer.seek(Duration.millis(mp3Slider.getValue() * 100));
            UPDATE_CHECK = true;
        }
    }

    @FXML
    protected void sliderDrag() {
        UPDATE_CHECK = false;
    }

    @FXML
    protected void moveTimeForward() {
        if (mplayer != null) {
            mplayer.seek(Duration.millis(mplayer.getCurrentTime().toMillis() + 10000));
        }
    }

    @FXML
    protected void moveTimeBack() {
        if (mplayer != null) {
            mplayer.seek(Duration.millis(mplayer.getCurrentTime().toMillis() - 10000));
        }
    }

    @FXML
    protected void moveTimeForwardLittle() {
        if (mplayer != null) {
            mplayer.seek(Duration.millis(mplayer.getCurrentTime().toMillis() + 200));
        }
    }

    @FXML
    protected void moveTimeBackLittle() {
        if (mplayer != null) {
            mplayer.seek(Duration.millis(mplayer.getCurrentTime().toMillis() - 200));
        }
    }

    public void updateMP3() {

        logger.debug("----- Executing updateMP3");
        long timer = System.currentTimeMillis();

        changeCRO();

        //check if title field has parenthesis that start with "ft " and if so, move the string to the artist field
        if (textTitle.getText().contains("(ft ")) {
            String titleString = textTitle.getText();
            int startOfFTString = titleString.indexOf("(ft ");
            textArtist.setText(textArtist.getText() + " ft " + titleString.substring(startOfFTString + 4, titleString.indexOf(")")));
            textTitle.setText(titleString.substring(0, startOfFTString));
        }
        if (dropGenre.getSelectionModel().getSelectedItem().equals("Instrumental") && textTitle.getText().endsWith(" (i)")) {
            String replace = textTitle.getText().replaceAll(" \\(i\\)", " (Instrumental)");
            logger.debug("replacing: " + textTitle.getText() + " with: " + replace);
            textTitle.setText(replace);
        }


        if (!buttonUpdateSongs.isDisable()) {

            Song dataChange = new Song();
            dataChange.setArtist(textArtist.getText());
            //if there's no album set, set it to title
            if (textAlbum.getText().isBlank() || Objects.equals(textAlbum.getText(), "N/A")) {
                textAlbum.setText(textTitle.getText());
            }
            dataChange.setAlbum(textAlbum.getText());
            dataChange.setTitle(textTitle.getText());
            dataChange.setComposer(textComposer.getText());
            //if there's no year set, set it to current year
            if (textYear.getText().isBlank()) {
                textYear.setText(String.valueOf(Year.now().getValue()));
            }
            dataChange.setYear(MyStringUtils.parseYear(textYear.getText()));
            dataChange.setGenre(dropGenre.getValue());
            dataChange.setPublisher(textPublisher.getText());
            dataChange.setISRC(textISRC.getText());
            dataChange.setDone(checkDone.isSelected());

            buttonUpdateSongs.setDisable(true);
            List<Song> selectedSongs = new ArrayList<>(songDatabaseTable.getSelectionModel().getSelectedItems());
            for (Song song : selectedSongs) {

                logger.debug("Starting song: "+(System.currentTimeMillis() - timer));
                MyID3 id3 = ID3Reader.getTag(new File(song.getFileLoc()));

                //if there's no year set, set it to current year

                if (!dataChange.getArtist().equals("<?>")) id3.setFrame(ID3Header.ARTIST, dataChange.getArtist());
                if (!dataChange.getTitle().equals("<?>")) id3.setFrame(ID3Header.TITLE, dataChange.getTitle());
                if (!dataChange.getAlbum().equals("<?>")) id3.setFrame(ID3Header.ALBUM, dataChange.getAlbum());
                if (!dataChange.getPublisher().equals("<?>"))
                    id3.setFrame(ID3Header.PUBLISHER, dataChange.getPublisher());
                if (!dataChange.getComposer().equals("<?>")) id3.setFrame(ID3Header.COMPOSER, dataChange.getComposer());
                if (!textYear.getText().equals("<?>"))
                    id3.setFrame(ID3Header.YEAR, dataChange.getYear().toString());
                id3.setFrame(ID3Header.LENGTH, String.valueOf(song.getDuration()));
                if (dataChange.getDone()) {
                    id3.setFrame(ID3Header.KEY, "true");
                } else {
                    id3.setFrame(ID3Header.KEY, " ");
                }
                if (!dataChange.getGenre().isEmpty()) id3.setFrame(ID3Header.GENRE, dataChange.getGenre());
                if (!dataChange.getISRC().equals("<?>")) id3.setFrame(ID3Header.ISRC, dataChange.getISRC());


                String renameResult = song.getFileLoc();
                if (dataChange.getDone()) {
                    renameResult = renameFile(song.getFileLoc(), id3.getData(ID3Header.GENRE).toLowerCase(), id3.getData(ID3Header.ARTIST),
                            id3.getData(ID3Header.TITLE), dataChange.getDone());
                }
                if (!renameResult.isEmpty()) {
                    updateSongEntry(id3, song.getId(), renameResult);
                    FileUtils.writeToMP3(id3, renameResult, checkDone.isSelected());
                }
                if (!renameResult.equals(song.getFileLoc())) {
                    if (mplayer != null) {
                        if (mplayer.getStatus() == MediaPlayer.Status.PLAYING) {
                            buttonPlay.setText("Play");
                            mplayer.pause();
                        }
                    }
                }
                logger.debug("Ending song: "+(System.currentTimeMillis() - timer));
            }
        }

        updateTable();
        buttonUpdateSongs.setDisable(false);
        handleMultiSelectFields();
        checkFields();
        logger.debug("----- ending updateMP3, time: " + (System.currentTimeMillis() - timer));
    }

    private void openMediaFile(String fileLoc) {
        try {
            // Create a temporary file in the system's temporary directory
            Path tempFile = Files.createTempFile("mp3_temp", ".mp3");
            Path sourcePath = Path.of(fileLoc);

            // Copy the original file to the temporary file
            Files.copy(sourcePath, tempFile, StandardCopyOption.REPLACE_EXISTING);

            // Ensure temporary file is deleted when JVM exits
            tempFile.toFile().deleteOnExit();

            // Close existing media stream if any
            closeMediaStream();

            // Create Media and MediaPlayer
            String mp3Path = tempFile.toUri().toASCIIString();
            Media mp3Media = new Media(mp3Path);
            mplayer = new MediaPlayer(mp3Media);

            // Set slider maximum based on song duration
            Song selectedSong = songDatabaseTable.getSelectionModel().getSelectedItem();
            if (selectedSong != null) {
                mp3Slider.setMax(selectedSong.getDuration() / 100.0);
            }
        } catch (IOException ex) {
            logger.error("Failed to open media file", ex);
        }
    }


    private void closeMediaStream() {
        if (mplayer != null) {
            try {
                mplayer.stop();
                mplayer.dispose();
            } catch (Exception ex) {
                logger.error("could not close media stream: ", ex.getCause());
            }
        }
    }

    public void addSong2DB() {
        //logger.debug("----- Executing addSong2DB");
        File mp3 = FileUtils.openFile("MP3 files (*.mp3)", "mp3", SongGlobal.getCurrentFolder());
        if (mp3 != null) {
            SongGlobal.setCurrentFolder(mp3.getParent());
            FileUtils.addMP3(mp3.toPath(), EDITOR_NAME);
            updateTable();
        }
        //logger.debug("----- ending addSong2DB");
    }

    public void revertID3() {
        //logger.debug("----- Executing revertID3");
        boolean result = Popups.giveConfirmAlert("Unsaved changes",
                "You are resetting the ID3 changes you made for this MP3",
                "Do you want to load the old data without saving the changes?");

        if (result) {
            updateTextFields(songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc());
            checkFields();
        }

        //logger.debug("----- ending revertID3");
    }

    public void changeVolume() {
        labelVolume.setText("Volume: " + String.format("%.0f", volumeSlider.getValue()) + "%");
        if (mplayer != null) {
            mplayer.setVolume(volumeSlider.getValue() / 100);
        }
    }

    public void copyID3() {
        //logger.debug("----- Executing copyID3");

        SongGlobal.setCopiedID3(ID3Reader.getTag(new File(songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc())));

        //logger.debug("----- ending copyID3");
    }

    public void pasteID3() {
        //logger.debug("----- Executing pasteID3");

        boolean confirm = Popups.giveConfirmAlert("Warning",
                "You're about to overwrite ID3 data",
                "Please comfirm your action");

        if (confirm) {
            String fileLoc = songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc();
            FileUtils.writeToMP3(SongGlobal.getCopiedID3(), fileLoc, checkDone.isSelected());
            updateSongEntry(SongGlobal.getCopiedID3(), SongRepository.getFileID(fileLoc), fileLoc);
            updateTextFields(fileLoc);
            updateTable();
        }

        //logger.debug("----- ending pasteID3");
    }

    public void deleteFile() {
        //logger.debug("----- Executing deleteFile");

        String[] dialogData = {"Database entry", "ID3 data", "File"};

        ChoiceDialog<String> dialog = new ChoiceDialog<>(dialogData[2], dialogData);
        dialog.setTitle("Delete");
        dialog.setHeaderText("Select what you want to delete");

        String result = dialog.showAndWait().orElse(null);
        if (result != null) {
            List<Song> deleteList = new ArrayList<>(songDatabaseTable.getSelectionModel().getSelectedItems());
            for (Song song : deleteList) {
                if (result.equals("File")) {
                    boolean deleted = true;
                    try {
                        Files.delete(Path.of(song.getFileLoc()));
                    } catch (IOException er) {
                        logger.error("can't delete file: ", er);
                        deleted = false;
                    }
                    if (deleted) SongRepository.delete(song);
                } else if (result.equals("Database entry")) {
                    SongRepository.delete(song);
                } else {
                    logger.debug("code to delete id3 tag here");
                }
            }
            updateTable();
        }

        //logger.debug("----- ending deleteFile");
    }

    public void changeCRO() {
        textArtist.setText(MyStringUtils.replaceCroChars(textArtist.getText(), ID3Header.ARTIST, checkCase.isSelected()));
        textTitle.setText(MyStringUtils.replaceCroChars(textTitle.getText(), ID3Header.TITLE, checkCase.isSelected()));
        textAlbum.setText(MyStringUtils.replaceCroChars(textAlbum.getText(), ID3Header.ALBUM, checkCase.isSelected()));
        textPublisher.setText(MyStringUtils.replaceCroChars(textPublisher.getText(), ID3Header.PUBLISHER, true));
        textComposer.setText(MyStringUtils.replaceCroChars(textComposer.getText(), ID3Header.COMPOSER, true));
    }

    public void changeCase() {
        textArtist.requestFocus();
        textArtist.setText(MyStringUtils.changeCaseOfString(textArtist.getText()));
        textTitle.setText(MyStringUtils.changeCaseOfString(textTitle.getText()));
        textAlbum.setText(MyStringUtils.changeCaseOfString(textAlbum.getText()));
    }

    private String generateNewFilename(String oldFile, boolean checkNew, String year, String genre, String artist, String title, boolean isDone) {
        String newFileLoc = artist + " - " + title + ".mp3";
        // replace : and / with _
        newFileLoc = newFileLoc.replaceAll("[:/]", "_");

        if (!isDone && !checkNew) {
            newFileLoc = Paths.get(oldFile).getParent() + "\\" + newFileLoc;
        } else {
            if (genre.equals("pop")) {
                genre = "";
            } else if (genre.equals("domoljubne")) {
                genre = "cro\\" + genre;
            }

            year = year + "\\";

            List<String> foldersWithNoYear = Arrays.asList(
                    "religiozne", "oldies", "x-mas", "cro\\domoljubne", "country", "slow", "metal", "navijacke", "rock",
                    "jazz", "dance", "trance", "electronic", "acoustic", "funk", "blues", "reggae"
            );
            if (foldersWithNoYear.contains(genre)) {
                year = "";

            }

            // folders that have a different name
            if (genre.equals("acoustic"))
                genre = "akustika";
            if (genre.equals("club"))
                genre = "clubbing";

            if (!genre.isEmpty()) genre += "\\";
            newFileLoc = NETWORK_FOLDER + "Songs\\" + genre + year + newFileLoc;

        }
        return newFileLoc;
    }

    //TODO: this part needs to check if all the fields are there so it needs to be handled earlier, probably in updateMP3()
    public String renameFile(String oldFileLoc, String genre, String artist, String title, boolean isDone) {
        //logger.debug("----- Executing renameFile");
        String newFileLoc = generateNewFilename(oldFileLoc, false, textYear.getText(), genre, artist, title, isDone);

        if (genre.isEmpty() && isDone) {
            Popups.giveInfoAlert("file rename error",
                    "no genre selected",
                    "please select genre and try again");
            return "";
        }

        Path filePath = Path.of(newFileLoc);
        boolean folderExists = Files.exists(filePath.getParent());
        boolean mkdResult = true;
        if (!folderExists) {
            mkdResult = new File(filePath.getParent().toString()).mkdirs();
        }
        if (!folderExists && !mkdResult) {
            logger.debug("creating folder failed:" + newFileLoc);
        }

        File oldFile = new File(oldFileLoc);
        File newFile = new File(newFileLoc);
        if (!oldFile.getAbsolutePath().equals(newFile.getAbsolutePath())) {
            //logger.debug("artist and title: x" + artist + "x - x" + title+"x");
            if (!artist.isEmpty() && !title.isEmpty()) {
                if (!oldFile.renameTo(newFile)) {
                    Popups.giveInfoAlert("Error",
                            "Your file can not be renamed",
                            newFile.getAbsolutePath() + " already exists or is in use.");

                    if (SongRepository.getFileID(newFileLoc) == null) {
                        FileUtils.addMP3(filePath, EDITOR_NAME);
                    }
                    updateTable();

                    return "";
                }
            } else {
                Popups.giveInfoAlert("Error",
                        "Your file can not be renamed",
                        "no artist or title");
                return "";
            }
        }
        songDatabaseTable.getItems();
        String fileLabel = newFile.getName();
        mp3Label.setText(fileLabel.replaceAll("(?i).mp3", ""));
        //logger.debug("----- ending renameFile");

        return newFileLoc;
    }

    /**
     * Updates the song entry in the database with the new data
     *
     * @param id3        the new id3 data
     * @param databaseID the id of the song in the database
     * @param fileLoc    the file location of the song
     */
    public void updateSongEntry(MyID3 id3, Integer databaseID, String fileLoc) {
        //logger.debug("----- Executing updateSongEntry");
        Song song = ID3v2Utils.songDataFromID3(id3, fileLoc, EDITOR_NAME);
        song.setId(databaseID);
        song.setEditor(EDITOR_NAME);
        SongRepository.addSong(song);
        //logger.debug("----- ending updateSongEntry");
    }

    public boolean checkArtistField(String artist) {
        if (artist.isEmpty()) {
            textArtist.setStyle("-fx-background-color: #" + AVERAGE_BACKGROUND_COLOR);
            return false;
        } else if (checkInvalidChars(artist)) {
            textArtist.setStyle("-fx-background-color: #" + CHANGED_BACKGROUND_COLOR);
            return true;
        } else {
            textArtist.setStyle("-fx-background-color: #" + DEFAULT_BACKGROUND_COLOR);
            return false;
        }
    }

    public boolean checkComposerField(String composer) {
        if (composer.isEmpty()) {
            textComposer.setStyle("-fx-background-color: #" + AVERAGE_BACKGROUND_COLOR);
            return false;
        } else if (checkInvalidChars(composer)) {
            textComposer.setStyle("-fx-background-color: #" + CHANGED_BACKGROUND_COLOR);
            return true;
        } else {
            textComposer.setStyle("-fx-background-color: #" + DEFAULT_BACKGROUND_COLOR);
            return false;
        }
    }

    public boolean checkTitleField(String title) {
        if (title.isEmpty()) {
            textTitle.setStyle("-fx-background-color: #" + AVERAGE_BACKGROUND_COLOR);
            return false;
        } else if (checkInvalidChars(title)) {
            textTitle.setStyle("-fx-background-color: #" + CHANGED_BACKGROUND_COLOR);
            return true;
        } else {
            textTitle.setStyle("-fx-background-color: #" + DEFAULT_BACKGROUND_COLOR);
            return false;
        }
    }

    public boolean checkInvalidChars(String text) {
        if (text == null || text.equals("<?>"))
            return false;

        return text.contains("%") || text.contains("?");
    }


    /**
     * Chekcs for invalid fields and colors them accordingly
     */
    public void checkFields() {

        if (!songDatabaseTable.getSelectionModel().getSelectedItems().isEmpty()) {
            String artist = textArtist.getText() == null ? "" : textArtist.getText();
            boolean artistCheck = checkArtistField(artist);

            String composer = textComposer.getText() == null ? "" : textComposer.getText();
            boolean composerCheck = checkComposerField(composer);

            String title = textTitle.getText() == null ? "" : textTitle.getText();
            boolean titleCheck = checkTitleField(title);

            if (textYear.getText() != null && !textYear.getText().isEmpty()) {
                textYear.setStyle("-fx-background-color: #" + DEFAULT_BACKGROUND_COLOR);
            } else {
                textYear.setStyle("-fx-background-color: #" + AVERAGE_BACKGROUND_COLOR);
            }

            if (textAlbum.getText() != null && !textAlbum.getText().isEmpty()) {
                textAlbum.setStyle("-fx-background-color: #" + DEFAULT_BACKGROUND_COLOR);
            } else {
                textAlbum.setStyle("-fx-background-color: #" + AVERAGE_BACKGROUND_COLOR);
            }

            if (textPublisher.getText() != null && !textPublisher.getText().isEmpty()) {
                textPublisher.setStyle("-fx-background-color: #" + DEFAULT_BACKGROUND_COLOR);
            } else {
                textPublisher.setStyle("-fx-background-color: #" + AVERAGE_BACKGROUND_COLOR);
            }

            if (dropGenre.getValue() != null && !dropGenre.getValue().isEmpty()) {
                dropGenre.setStyle("-fx-background-color: #" + DEFAULT_BACKGROUND_COLOR);
            } else {
                dropGenre.setStyle("-fx-background-color: #" + AVERAGE_BACKGROUND_COLOR);
            }

            boolean disableUpdateButton = artistCheck || composerCheck || titleCheck;
            checkFilename(disableUpdateButton);
        }

    }

    private void checkFilename(boolean disableUpdateButton) {
        //logger.debug("checking name goes here");
        String tempGenre = dropGenre.getSelectionModel().getSelectedItem();
        if (tempGenre == null) {
            tempGenre = "";
        }
        String newFileLoc = generateNewFilename(songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc(),
                true, textYear.getText(), tempGenre, songDatabaseTable.getSelectionModel().getSelectedItem().getArtist(),
                songDatabaseTable.getSelectionModel().getSelectedItem().getTitle(), checkDone.isSelected());
        boolean found = new File(newFileLoc).exists();
        buttonUpdateSongs.setDisable(disableUpdateButton);
        if (!songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc().equalsIgnoreCase(newFileLoc)) {
            //logger.debug("names do not match!, checking file: " + newFileLoc);

            //if the song exists, update is disabled... that should work for now but maybe requires rethink...
            buttonUpdateSongs.setDisable((found && checkDone.isSelected() && !songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc().contains("Z:")) || disableUpdateButton);

            if (found) {
                buttonUpdateSongs.setStyle("-fx-background-color: #" + CHANGED_BACKGROUND_COLOR);
                mp3Label.setText(newFileLoc.replaceAll("(?i)\\.mp3", ""));
            } else {
                AtomicReference<String> foundAlt = new AtomicReference<>("");
                dropGenre.getItems().forEach(genre -> {
                            String getYear = textYear.getText();
                            if (getYear != null) {
                                getYear = getYear.replaceAll("\\D", "");
                            }
                            if (getYear == null || getYear.isEmpty()) {
                                getYear = Year.now().toString();
                            }
                            //logger.debug("getYear:-" + getYear + "-");
                            int year = Integer.parseInt(getYear);
                            for (int testingYear = year - 2; testingYear <= year + 1; testingYear++) {
                                //logger.debug("testing year: " + testingYear);
                                String newFileLocAlt = generateNewFilename(songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc(),
                                        true, testingYear + "", genre, songDatabaseTable.getSelectionModel().getSelectedItem().getArtist(),
                                        songDatabaseTable.getSelectionModel().getSelectedItem().getTitle(), checkDone.isSelected());
                                if (new File(newFileLocAlt).exists()) {
                                    foundAlt.set(newFileLocAlt.replaceAll("Z:\\\\Songs\\\\", "").replaceAll("\\\\", " - "));
                                    logger.debug("found alternative file: " + foundAlt.get());
                                }
                            }
                        }
                );
                if (!foundAlt.get().isEmpty()) {
                    buttonUpdateSongs.setStyle("-fx-background-color: #" + AVERAGE_BACKGROUND_COLOR);
                    mp3Label.setText(foundAlt.get().replaceAll("(?i)\\.mp3", ""));
                } else {
                    buttonUpdateSongs.setStyle("-fx-background-color: #" + DEFAULT_BACKGROUND_COLOR);
                    mp3Label.setText(new File(songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc()).getName().replaceAll("(?i).mp3", ""));
                }
                //logger.debug("set colour back");
            }
        } else {
            buttonUpdateSongs.setStyle("-fx-background-color: #" + DEFAULT_BACKGROUND_COLOR);
            mp3Label.setText(new File(songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc()).getName().replaceAll("(?i).mp3", ""));
            //logger.debug("set colour back");
        }

    }

    @FXML
    public void filterTable() {
        String[] filter = textFilterFolder.getText().toLowerCase().split("[|]");

        filteredSongs.setPredicate(currentSearchSong -> {
            if (doneFilter.getSelectionModel().getSelectedIndex() == 1 && !currentSearchSong.getDone())
                return false;
            if (doneFilter.getSelectionModel().getSelectedIndex() == 2 && currentSearchSong.getDone())
                return false;
            String title = currentSearchSong.getTitle().toLowerCase();
            String artist = currentSearchSong.getArtist().toLowerCase();
            String album = currentSearchSong.getAlbum().toLowerCase();
            String genre = currentSearchSong.getGenre().toLowerCase();
            String publisher = currentSearchSong.getPublisher().toLowerCase();
            for (String filterString : filter) {
                //System.out.println(filterString);
                if (!title.contains(filterString) &&
                        !artist.contains(filterString) &&
                        !album.contains(filterString) &&
                        !genre.contains(filterString) &&
                        !publisher.contains(filterString) &&
                        !currentSearchSong.getFileLoc().toLowerCase().contains(filterString))
                    return false;
            }
            if (userFilter.getSelectionModel().getSelectedIndex() != 0 &&
                    !userFilter.getSelectionModel().getSelectedItem().equalsIgnoreCase(currentSearchSong.getEditor()))
                return false;

            try {
                if (truncatedFilter.getSelectionModel().getSelectedIndex() == 1 &&
                        !TruncatedUtil.isTruncated(currentSearchSong))
                    return false;
            } catch (IllegalAccessException e) {
                logger.error("error while truncate checking: ", e);
            }
            return true;
        });

        songDatabaseTable.setItems(sortedSongs);

        labelSongNumber.setText("showing " + filteredSongs.size() + " out of " + songList.size() + " songs with criteria: ");

    }

    public void openLegacyData() throws IOException {
        logger.debug("Here we open new window");

        String fxmlLocation = "/prodo/marc/gosling/view/legacyAccessDatabaseViewer.fxml";
        SceneController.openWindow(fxmlLocation, false);

    }


    public void googleSong() {
        Song song = songDatabaseTable.getSelectionModel().getSelectedItem();
        String uri = song.getArtist() + " " + song.getTitle();
        uri = "https://www.google.com/search?q=" + uri;
        openURL(uri, "+");
    }

    public void spotSong() {
        Song song = songDatabaseTable.getSelectionModel().getSelectedItem();
        String uri = song.getArtist() + " " + song.getTitle();
        uri = uri.toLowerCase();
        uri = uri.replace(" ft ", " ");
        uri = uri.replace(" & ", " ");
        uri = uri.replace(" x ", " ");
        uri = uri.replace(" i ", " ");
        uri = "https://open.spotify.com/search/" + uri;
        openURL(uri, "%20");
    }

    public void zampSong() {
        Song song = songDatabaseTable.getSelectionModel().getSelectedItem();
        String uri = song.getTitle();
        uri = "https://www.zamp.hr/baza-autora/rezultati-djela/pregled/" + uri;
        openURL(uri, "+");
    }

    public void discogSong() {
        Song song = songDatabaseTable.getSelectionModel().getSelectedItem();
        String uri = song.getArtist() + " " + song.getTitle();
        uri = "https://www.discogs.com/search/?type=all&q=" + uri;
        openURL(uri, "+");
    }

    private void openURL(String uri, String space) {
        uri = uri.replace(" ", space);
        uri = uri.replaceAll("[\\[\\]]", "");
        Desktop desktop = Desktop.isDesktopSupported() ? Desktop.getDesktop() : null;
        if (desktop != null && desktop.isSupported(Desktop.Action.BROWSE)) {
            try {
                desktop.browse(URI.create(uri));
            } catch (Exception err) {
                logger.debug("Error:", err);
            }
        }
    }

    public void testFiles(DragEvent dragEvent) {
        if (dragEvent.getGestureSource() != songDatabaseTable
                && dragEvent.getDragboard().hasFiles()) {
            List<File> list = dragEvent.getDragboard().getFiles();
            List<Path> mp3List = new ArrayList<>();
            int zipCounter = 0;

            for (File file : list) {
                if (file.isDirectory()) {
                    try {
                        mp3List.addAll(FileUtils.getFileListFromFolder(file, "mp3"));
                    } catch (IOException e) {
                        logger.error("could not read files in folder: ", e);
                    }
                } else if (file.toString().toLowerCase().endsWith(".mp3")) {
                    mp3List.add(Path.of(file.getAbsolutePath()));
                }

                //TODO: this checks for number of MP3s in a zip file, eventually maybe add a choice what to extract from a zip?
                if (file.toString().endsWith(".zip")) {
                    Enumeration<? extends ZipEntry> files;
                    try (ZipFile zip = new ZipFile(String.valueOf(file))) {
                        files = zip.entries();
                        while (files.hasMoreElements()) {
                            ZipEntry zipFile = files.nextElement(); 
                            String filename = zipFile.getName();
                            if (filename.contains("/"))
                                filename = filename.substring(filename.lastIndexOf("/") + 1);
                            if (filename.toLowerCase().endsWith(".mp3")) {
                                zipCounter++;
                            }
                        }
                    } catch (IOException catchError) {
                        logger.error("error handling zip file!", catchError);
                    }

                }

            }

            SongGlobal.setMP3List(mp3List);
            if (!SongGlobal.getMP3List().isEmpty()) {
                if (songDatabaseTable.getSelectionModel().getSelectedItem() == null) {
                    SongGlobal.setEditor(EDITOR_NAME);
                    logger.debug("Adding files with: "+ EDITOR_NAME);
                }
                putMP3ListIntoDB();
            } else {
                Popups.giveInfoAlert("Error importing",
                        "There were no mp3 files to import",
                        list.toString());
            }

            if (zipCounter > 0) Popups.giveInfoAlert("Zip file(s) detected",
                    "MP3 files in zip file(s) detected: ",
                    zipCounter + "");
        }
    }

    /**
     * Switches the table from short to long and vice versa
     */
    public void switchTable() {
        if (!tableEditor.isVisible()) {
            tableID.setVisible(true);
            tableComposer.setVisible(true);
            tableEditor.setVisible(true);
            //tableFileLoc.setVisible(true);
            tablePublisher.setVisible(true);
            tableDone.setVisible(true);
            tableToggleButton.setText("-");
            songDatabaseTable.setMaxWidth(getTableWidth());
        } else {
            tableID.setVisible(false);
            tableComposer.setVisible(false);
            tableEditor.setVisible(false);
            //tableFileLoc.setVisible(false);
            tablePublisher.setVisible(false);
            tableDone.setVisible(false);
            tableToggleButton.setText("+");
            songDatabaseTable.setMaxWidth(getTableWidth());
        }
    }

    private double getTableWidth() {
        double width = 20;
        for (TableColumn<Song, ?> column : songDatabaseTable.getColumns())
            if (column.isVisible()) width += column.getWidth();

        //logger.debug(width);
        return width;
    }

    public void listTag() {
        String id3File = songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc();
        MyID3 tempID3 = ID3Reader.getTag(new File(id3File));
        logger.debug(tempID3.listFrames());
        Popups.giveInfoAlert("ID3 tag content for: ", id3File, tempID3.listFrames() + "   ---" + tempID3.getSize() + "bytes");
    }


    public void filterChange() {
        textFilterFolder.setText(songDatabaseTable.getSelectionModel().getSelectedItem().getArtist() + "|" +
                songDatabaseTable.getSelectionModel().getSelectedItem().getTitle());

        filterTable();
    }

    public void autofillPublisher(KeyEvent keyEvent) {
        byte[] chars = keyEvent.getCharacter().getBytes();
        boolean special = chars[0] < 31 || keyEvent.isShortcutDown() || chars[0] > 126;
        String searchTerm = textPublisher.getText().toUpperCase();

        if (!special && textPublisher.getCaretPosition() == textPublisher.getLength()) {
            for (String publisher : publisherList) {
                if (publisher.toUpperCase().startsWith(searchTerm)) {
                    textPublisher.deselect();
                    textPublisher.setText(publisher);
                    textPublisher.positionCaret(searchTerm.length());
                    textPublisher.selectEnd();
                    break;
                }
            }
        }
        checkFields();
    }

    public void openFolder() {
        String fileLoc = new File(songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc()).getParent();
        String file = new File(songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc()).getName();
        try {
            Runtime.getRuntime().exec("explorer.exe /select," + fileLoc + "\\" + file);
        } catch (IOException e) {
            logger.error("Error opening folder", e);
        }
    }

    public void nextMP3() {
        int index = songDatabaseTable.getSelectionModel().getSelectedIndex();
        //logger.debug("index: " + index);
        if (index < songDatabaseTable.getItems().size() - 1) {
            index++;
            songDatabaseTable.getSelectionModel().clearSelection();
            songDatabaseTable.getSelectionModel().select(index);
            updateTextFields(songDatabaseTable.getSelectionModel().getSelectedItem().getFileLoc());
        }
        if (index != -1) playMP3();
    }

    public void togleTime() {
        TIME_LEFT = !TIME_LEFT;
    }

    public void expandGenre() {
        dropGenre.getItems().clear();
        dropGenre.getItems().addAll(getGenres(buttonExpandGenre.getText()));
        if (buttonExpandGenre.getText().equals("-")) {
            buttonExpandGenre.setText("+");
        } else {
            buttonExpandGenre.setText("-");
        }
    }
}