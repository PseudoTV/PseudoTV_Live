<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<window>
    <backgroundcolor>0x00000000</backgroundcolor>
    <onload>SetProperty(plugin.video.pseudotv.live.OVERLAY,True,10000)</onload>
    <onunload>SetProperty(plugin.video.pseudotv.live.OVERLAY,False,10000)</onunload> 
    <controls>
      <control type="group" id="40011">
        <posx>0</posx>
        <posy>0</posy>
        <description>Background !Playing</description>
        
        <visible>true</visible>
        <!-- <visible>!Player.HasVideo + !Player.Playing + !Player.Paused</visible> -->
        <control type="group">
          <description>Background Dynamic</description>
          <control type="image"> 
            <description>Hide Background</description>
            <width>auto</width>
            <height>auto</height>
            <aspectratio>scale</aspectratio>
            <align>center</align>
            <aligny>center</aligny>
            <colordiffuse>black</colordiffuse>
            <texture>colors/white.png</texture>
          </control>
          <control type="image"> 
            <width>auto</width>
            <height>auto</height>
            <texture>backgrounds/giphy.gif</texture>
            <aspectratio scalediffuse="false" align="center" aligny="center">scale</aspectratio>
          </control>
          <control type="grouplist">
            <posx>1440</posx>
            <posy>850</posy>
            <width>480</width>
            <itemgap>1</itemgap>
            <orientation>vertical</orientation>
            <control type="label" id="30002">
                <description>Time</description>
                <align>center</align>
                <aligny>center</aligny>
                <font>font_clock</font>
                <shadowcolor>text_shadow</shadowcolor>
                <height>60</height>
                <label>[B]$INFO[System.Time][/B]</label>
            </control>
            <control type="image">
                <height>90</height>
                <texture>splashtext.png</texture>
                <aspectratio scalediffuse="true" align="center" aligny="center">keep</aspectratio>
            </control>
          </control>
          
          <control type="grouplist">
            <centertop>65%</centertop>
            <centerleft>50%</centerleft>
            <width>960</width>
            <itemgap>5</itemgap>
            <orientation>vertical</orientation>
            <control type="image"> 
                <description>Background Logo</description>
                <height>240</height>
                <aspectratio scalediffuse="true" align="center" aligny="top">keep</aspectratio>
                <texture>$INFO[Container(40000).ListItem(0).Art(icon)]</texture>
            </control>
            <control type="textbox">
                <height>90</height>
                <width>auto</width>
                <font>font27</font>
                <scroll>true</scroll>
                <align>center</align>
                <aligny>center</aligny>
                <textcolor>white</textcolor>
                <shadowcolor>text_shadow</shadowcolor>
                <scrolltime>600</scrolltime>
                <autoscroll delay="5000" time="1000">false</autoscroll>
                <label>$INFO[Container(40000).ListItem(0).Property(name),[B]You're Watching:[/B] ,] [CR] $INFO[Container(40000).ListItem(1).Label,[B]Up Next:[/B] ,] $INFO[Container(40000).ListItem(1).Property(episodelabel), - ,] </label>
            </control>
          </control>
        </control>
        
        <control type="image" id="40001">
            <description>Background Static</description>
            <width>auto</width>
            <height>auto</height>
            <aspectratio scalediffuse="true" align="center" aligny="center">scale</aspectratio>
            <texture>backgrounds/static.gif</texture>
        </control>
        <control type="image">
            <centertop>50%</centertop>
            <centerleft>50%</centerleft>
            <width>960</width>
            <height>auto</height>
            <texture>splashtext.png</texture>
            <visible>Control.IsVisible(40001)</visible>
            <aspectratio scalediffuse="true" align="center" aligny="center">keep</aspectratio>
            <animation effect="fade" start="75" end="75" condition="True">Conditional</animation>
        </control>
      </control>
      
      <control type="group" id="39999">
        <posx>0</posx>
        <posy>0</posy>
        <description>Background Playing</description>
        <!-- <visible>Player.HasVideo + Player.Playing</visible> -->
        <visible>false</visible>
        <control type="image"> 
          <description>Hide Background</description>
          <width>auto</width>
          <height>auto</height>
          <aspectratio>scale</aspectratio>
          <align>center</align>
          <aligny>center</aligny>
          <colordiffuse>black</colordiffuse>
          <texture>colors/white.png</texture>
        </control>
        <!-- <control type="videowindow" id="41000"> -->
          <!-- <description>Video Overlay</description> -->
          <!-- <posx>0</posx> -->
          <!-- <posy>0</posy> -->
          <!-- <width>auto</width> -->
          <!-- <height>auto</height> -->
          <!-- <align>center</align> -->
          <!-- <aligny>center</aligny> -->
        <!-- </control> -->
                
        <control type="group">
          <description>Skip/Startover</description>
          <left>222</left>
          <top>888</top>
          <visible>false</visible>
          <control type="button" id="41002">
            <width>auto</width>
            <height>128</height>
            <texturefocus colordiffuse="">Skip/startover.png</texturefocus>
            <texturenofocus colordiffuse="">Skip/startover.png</texturenofocus>
            <label>[B]Start Over?[/B]</label>
            <font>font_clock</font>
            <textcolor>FFFFFFFF</textcolor>
            <shadowcolor>text_shadow</shadowcolor>
            <aspectratio>keep</aspectratio>
            <textoffsetx>256</textoffsetx>
            <textoffsety></textoffsety>
            <pulseonselect>true</pulseonselect>
          </control>
        </control>
        
        <control type="textbox" id="41003">
            <description>UpNext</description>
            <left>128</left>
            <top>952</top>
            <width>1418</width>
            <height>36</height>
            <font>font12</font>
            <textcolor>white</textcolor>
            <shadowcolor>text_shadow</shadowcolor>
            <align>left</align>
            <aligny>center</aligny>
            <scrolltime>600</scrolltime>
            <autoscroll delay="5000" time="1000">true</autoscroll>
            <label>$INFO[Container(40000).ListItem(0).Label,[B]You're Watching:[/B] ,] [CR] $INFO[Container(40000).ListItem(1).Label,[B]Up Next:[/B] ,] $INFO[Container(40000).ListItem(1).Property(episodelabel), - ,] </label>
        </control>
      </control>
      
      <control type="image" id="41004">
        <description>Channel Bug</description>
        <left>1556</left>
        <top>920</top>
        <width>128</width>
        <height>128</height>
        <visible>!Control.IsVisible(40011)</visible>
        <aspectratio>keep</aspectratio>         
        <animation type="Conditional" condition="Control.IsVisible(41004)" reversible="false">
          <effect type="fade" start="0"   end="100"  time="2000" delay="500"/>
          <effect type="fade" start="100" end="25"   time="1000" delay="3000"/>
        </animation>
      </control>
      
      <control type="image" id="41005">
        <description>Screen Overlay</description>
        <left>0</left>
        <top>0</top>
        <width>auto</width>
        <height>auto</height>
        <aspectratio>scale</aspectratio>
        <texture></texture>
      </control>
      
      <control type="list" id="40000">
        <description>Meta Container</description>
        <itemlayout width="0" height="0">
        </itemlayout>
        <focusedlayout height="0" width="0">
        </focusedlayout>
      </control>
    </controls>
</window>